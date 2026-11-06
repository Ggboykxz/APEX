//! Project initialization — port of `apex/project.py` (`ProjectInitializer`).
//!
//! Analyzes a project directory to detect language, package manager, test
//! framework, LSP server, formatters, build system, structure, and
//! dependencies. Used by the `/init` and `/analyze` slash commands.
//!
//! Wired into the HTTP route `POST /api/v1/init`.

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use serde_json::Value;

/// Project initializer — analyzes a project directory to detect language,
/// package manager, test framework, LSP server, formatters, build system,
/// structure, and dependencies.
#[derive(Debug, Clone)]
pub struct ProjectInitializer {
    cwd: PathBuf,
}

impl ProjectInitializer {
    /// Create a new project initializer for the given working directory.
    pub fn new(cwd: impl AsRef<Path>) -> Self {
        Self {
            cwd: cwd.as_ref().to_path_buf(),
        }
    }

    /// Analyze the project and return a structured result.
    pub fn analyze(&self) -> ProjectAnalysis {
        let mut result = ProjectAnalysis::default();

        self._detect_language(&mut result);
        self._detect_package_manager(&mut result);
        self._detect_test_framework(&mut result);
        self._detect_lsp(&mut result);
        self._detect_formatters(&mut result);
        self._detect_build_system(&mut result);
        self._analyze_structure(&mut result);
        self._extract_info(&mut result);

        result
    }

    /// Analyze and write an AGENTS.md context file into the project root.
    /// Returns the path to the created file.
    pub fn create_context_file(&self) -> String {
        let analysis = self.analyze();
        let output = self.cwd.join("AGENTS.md");

        let mut lines: Vec<String> = Vec::new();
        lines.push(format!(
            "# {}",
            self.cwd.file_name().unwrap_or_default().to_string_lossy()
        ));
        lines.push(String::new());
        lines.push(format!(
            "Language: {}",
            analysis.language.as_deref().unwrap_or("unknown")
        ));
        lines.push(format!(
            "Package Manager: {}",
            analysis.package_manager.as_deref().unwrap_or("unknown")
        ));
        lines.push(format!(
            "Test Framework: {}",
            analysis.test_framework.as_deref().unwrap_or("unknown")
        ));
        lines.push(format!(
            "LSP Server: {}",
            analysis.lsp_server.as_deref().unwrap_or("not configured")
        ));
        lines.push(String::new());
        lines.push("## Available Scripts".to_string());

        for (name, cmd) in &analysis.scripts {
            lines.push(format!("- `{}`: {}", name, cmd));
        }

        lines.extend([
            "".to_string(),
            "## Project Structure".to_string(),
            "".to_string(),
            format!(
                "Source directories: {}",
                analysis.structure.src_dirs.join(", ")
            ),
            if analysis.structure.src_dirs.is_empty() {
                "none".to_string()
            } else {
                "".to_string()
            },
            format!(
                "Test directories: {}",
                analysis.structure.test_dirs.join(", ")
            ),
            if analysis.structure.test_dirs.is_empty() {
                "none".to_string()
            } else {
                "".to_string()
            },
            "".to_string(),
            "## Key Dependencies".to_string(),
        ]);

        for dep in analysis.dependencies.iter().take(20) {
            lines.push(format!("- {}", dep));
        }

        lines.extend(["".to_string(), "## Configuration Files".to_string()]);

        for cf in &analysis.structure.config_files {
            lines.push(format!("- {}", cf));
        }

        let content = lines.join("\n");
        std::fs::write(&output, &content).ok();
        output.to_string_lossy().to_string()
    }

    // ── Private detection methods ──────────────────────────────────────

    fn _detect_language(&self, result: &mut ProjectAnalysis) {
        if self.cwd.join("pyproject.toml").exists() {
            result.language = Some("python".to_string());
        } else if self.cwd.join("package.json").exists() {
            result.language = Some("javascript".to_string());
        } else if self.cwd.join("go.mod").exists() {
            result.language = Some("go".to_string());
        } else if self.cwd.join("Cargo.toml").exists() {
            result.language = Some("rust".to_string());
        } else if self.cwd.join("pom.xml").exists() {
            result.language = Some("java".to_string());
        } else if self.cwd.join("go.sum").exists() {
            result.language = Some("go".to_string());
        } else if self.cwd.join("requirements.txt").exists() {
            result.language = Some("python".to_string());
        } else if self.cwd.join("Gemfile").exists() {
            result.language = Some("ruby".to_string());
        }
    }

    fn _detect_package_manager(&self, result: &mut ProjectAnalysis) {
        if self.cwd.join("pyproject.toml").exists() {
            let content = fs::read_to_string(self.cwd.join("pyproject.toml")).unwrap_or_default();
            if content.contains("poetry") {
                result.package_manager = Some("poetry".to_string());
            } else {
                result.package_manager = Some("pip".to_string());
            }
        } else if self.cwd.join("package.json").exists() {
            if self.cwd.join("yarn.lock").exists() {
                result.package_manager = Some("yarn".to_string());
            } else if self.cwd.join("pnpm-lock.yaml").exists() {
                result.package_manager = Some("pnpm".to_string());
            } else {
                result.package_manager = Some("npm".to_string());
            }
        } else if self.cwd.join("go.mod").exists() {
            result.package_manager = Some("go mod".to_string());
        } else if self.cwd.join("Cargo.toml").exists() {
            result.package_manager = Some("cargo".to_string());
        } else if self.cwd.join("Gemfile").exists() {
            result.package_manager = Some("bundle".to_string());
        }
    }

    fn _detect_test_framework(&self, result: &mut ProjectAnalysis) {
        match result.language.as_deref() {
            Some("python") => {
                if self.cwd.join("pytest.ini").exists() {
                    result.test_framework = Some("pytest".to_string());
                } else if self.cwd.join("unittest.py").exists() {
                    result.test_framework = Some("unittest".to_string());
                } else if self.cwd.join("pyproject.toml").exists() {
                    if let Ok(content) = fs::read_to_string(self.cwd.join("pyproject.toml")) {
                        if content.contains("tool.pytest") {
                            result.test_framework = Some("pytest".to_string());
                        }
                    }
                }
            }
            Some("javascript") | Some("typescript") => {
                if self.cwd.join("package.json").exists() {
                    if let Ok(content) = fs::read_to_string(self.cwd.join("package.json")) {
                        if let Ok(pkg) = serde_json::from_str::<Value>(&content) {
                            let deps = pkg
                                .get("dependencies")
                                .and_then(|v| v.as_object())
                                .cloned()
                                .unwrap_or_default();
                            let dev_deps = pkg
                                .get("devDependencies")
                                .and_then(|v| v.as_object())
                                .cloned()
                                .unwrap_or_default();
                            let all_deps: Vec<&str> = deps
                                .keys()
                                .chain(dev_deps.keys())
                                .map(|s| s.as_str())
                                .collect();
                            if all_deps.contains(&"vitest") {
                                result.test_framework = Some("vitest".to_string());
                            } else if all_deps.contains(&"jest") {
                                result.test_framework = Some("jest".to_string());
                            } else if all_deps.contains(&"@playwright/test") {
                                result.test_framework = Some("playwright".to_string());
                            }
                        }
                    }
                }
            }
            Some("go") => {
                result.test_framework = Some("go test".to_string());
            }
            Some("rust") => {
                result.test_framework = Some("cargo test".to_string());
            }
            _ => {}
        }
    }

    fn _detect_lsp(&self, result: &mut ProjectAnalysis) {
        let lsp_map: &[(&str, &str)] = &[
            ("python", "pylsp"),
            ("javascript", "typescript-language-server"),
            ("typescript", "typescript-language-server"),
            ("go", "gopls"),
            ("rust", "rust-analyzer"),
            ("java", "java-language-server"),
            ("ruby", "solargraph"),
        ];
        if let Some(lang) = result.language.as_deref() {
            if let Some((_, lsp)) = lsp_map.iter().find(|(l, _)| *l == lang) {
                result.lsp_server = Some(lsp.to_string());
            }
        }
    }

    fn _detect_formatters(&self, result: &mut ProjectAnalysis) {
        match result.language.as_deref() {
            Some("python") => {
                result.formatters = vec!["black".to_string(), "ruff".to_string()];
            }
            Some("javascript") | Some("typescript") => {
                result.formatters = vec!["prettier".to_string(), "eslint".to_string()];
            }
            Some("go") => {
                result.formatters = vec!["gofmt".to_string(), "goimports".to_string()];
            }
            Some("rust") => {
                result.formatters = vec!["rustfmt".to_string(), "clippy".to_string()];
            }
            _ => {}
        }
    }

    fn _detect_build_system(&self, result: &mut ProjectAnalysis) {
        match result.language.as_deref() {
            Some("python") => {
                if self.cwd.join("Makefile").exists() {
                    result.build_system = Some("make".to_string());
                } else if self.cwd.join("setup.py").exists() {
                    result.build_system = Some("setuptools".to_string());
                }
            }
            Some("javascript") => {
                result.build_system = Some("npm".to_string());
            }
            Some("go") => {
                result.build_system = Some("go".to_string());
            }
            Some("rust") => {
                result.build_system = Some("cargo".to_string());
            }
            _ => {}
        }
    }

    fn _analyze_structure(&self, result: &mut ProjectAnalysis) {
        let ignore: &[&str] = &[
            ".git",
            "node_modules",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "dist",
            "build",
            ".pytest_cache",
            ".tox",
            "vendor",
        ];

        let mut src_dirs: Vec<String> = Vec::new();
        let mut test_dirs: Vec<String> = Vec::new();
        let mut config_files: Vec<String> = Vec::new();

        if let Ok(entries) = fs::read_dir(&self.cwd) {
            for entry in entries.flatten() {
                let path = entry.path();
                let name = path
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .into_owned();
                if name.starts_with('.') || ignore.contains(&name.as_str()) {
                    continue;
                }
                if path.is_dir() {
                    let lower = name.to_lowercase();
                    if lower.contains("src") || lower.contains("lib") || lower.contains("app") {
                        src_dirs.push(name);
                    } else if lower.contains("test") || lower.contains("spec") {
                        test_dirs.push(name);
                    }
                } else if path.is_file()
                    && matches!(
                        path.extension().and_then(|s| s.to_str()),
                        Some("json")
                            | Some("yaml")
                            | Some("yml")
                            | Some("toml")
                            | Some("ini")
                            | Some("cfg")
                            | Some("conf")
                            | Some("env")
                    )
                {
                    config_files.push(name);
                }
            }
        }

        result.structure = ProjectStructure {
            src_dirs,
            test_dirs,
            config_files,
        };
    }

    fn _extract_info(&self, result: &mut ProjectAnalysis) {
        if result.language == Some("python".to_string()) {
            if self.cwd.join("pyproject.toml").exists() {
                if let Ok(content) = fs::read_to_string(self.cwd.join("pyproject.toml")) {
                    if let Ok(data) = toml::from_str::<Value>(&content) {
                        result.scripts = data
                            .get("project")
                            .and_then(|v| v.get("scripts"))
                            .and_then(|v| v.as_object())
                            .map(|m| {
                                m.iter()
                                    .map(|(k, v)| (k.clone(), v.as_str().unwrap_or("").to_string()))
                                    .collect()
                            })
                            .unwrap_or_default();

                        result.dependencies = data
                            .get("project")
                            .and_then(|v| v.get("dependencies"))
                            .and_then(|v| v.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|d| d.as_str())
                                    .map(|d| d.split("==").next().unwrap_or(d).to_string())
                                    .collect()
                            })
                            .unwrap_or_default();

                        result.dev_dependencies = data
                            .get("project")
                            .and_then(|v| v.get("optional-dependencies"))
                            .and_then(|v| v.get("dev"))
                            .and_then(|v| v.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|d| d.as_str())
                                    .map(|d| d.split("==").next().unwrap_or(d).to_string())
                                    .collect()
                            })
                            .unwrap_or_default();
                    }
                }
            }
        } else if result.language == Some("javascript".to_string())
            && self.cwd.join("package.json").exists()
        {
            if let Ok(content) = fs::read_to_string(self.cwd.join("package.json")) {
                if let Ok(pkg) = serde_json::from_str::<Value>(&content) {
                    result.scripts = pkg
                        .get("scripts")
                        .and_then(|v| v.as_object())
                        .map(|m| {
                            m.iter()
                                .map(|(k, v)| (k.clone(), v.as_str().unwrap_or("").to_string()))
                                .collect()
                        })
                        .unwrap_or_default();
                    result.dependencies = pkg
                        .get("dependencies")
                        .and_then(|v| v.as_object())
                        .map(|m| m.keys().cloned().collect())
                        .unwrap_or_default();
                    result.dev_dependencies = pkg
                        .get("devDependencies")
                        .and_then(|v| v.as_object())
                        .map(|m| m.keys().cloned().collect())
                        .unwrap_or_default();
                }
            }
        }
    }
}

/// Result of project analysis.
#[derive(Debug, Clone, Default)]
pub struct ProjectAnalysis {
    pub language: Option<String>,
    pub package_manager: Option<String>,
    pub test_framework: Option<String>,
    pub lsp_server: Option<String>,
    pub formatters: Vec<String>,
    pub build_system: Option<String>,
    pub structure: ProjectStructure,
    pub dependencies: Vec<String>,
    pub dev_dependencies: Vec<String>,
    pub scripts: HashMap<String, String>,
}

/// Structure of a project directory.
#[derive(Debug, Clone, Default)]
pub struct ProjectStructure {
    pub src_dirs: Vec<String>,
    pub test_dirs: Vec<String>,
    pub config_files: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detect_python_project() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("pyproject.toml"),
            "[project]\nname = \"test\"\n",
        )
        .unwrap();
        std::fs::write(dir.path().join("requirements.txt"), "requests\n").unwrap();

        let initializer = ProjectInitializer::new(dir.path());
        let analysis = initializer.analyze();

        assert_eq!(analysis.language.as_deref(), Some("python"));
        assert_eq!(analysis.package_manager.as_deref(), Some("pip"));
    }

    #[test]
    fn detect_javascript_project() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("package.json"),
            r#"{"name":"test","dependencies":{"vitest":"^1.0"}}"#,
        )
        .unwrap();

        let initializer = ProjectInitializer::new(dir.path());
        let analysis = initializer.analyze();

        assert_eq!(analysis.language.as_deref(), Some("javascript"));
        assert_eq!(analysis.package_manager.as_deref(), Some("npm"));
        assert_eq!(analysis.test_framework.as_deref(), Some("vitest"));
    }

    #[test]
    fn detect_rust_project() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("Cargo.toml"),
            "[package]\nname = \"test\"\n",
        )
        .unwrap();

        let initializer = ProjectInitializer::new(dir.path());
        let analysis = initializer.analyze();

        assert_eq!(analysis.language.as_deref(), Some("rust"));
        assert_eq!(analysis.package_manager.as_deref(), Some("cargo"));
        assert_eq!(analysis.test_framework.as_deref(), Some("cargo test"));
        assert_eq!(analysis.build_system.as_deref(), Some("cargo"));
        assert_eq!(analysis.formatters, vec!["rustfmt", "clippy"]);
    }

    #[test]
    fn analyze_returns_structure() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        std::fs::create_dir_all(dir.path().join("tests")).unwrap();
        std::fs::write(dir.path().join("pyproject.toml"), "[project]\n").unwrap();

        let initializer = ProjectInitializer::new(dir.path());
        let analysis = initializer.analyze();

        assert!(analysis.structure.src_dirs.contains(&"src".to_string()));
        assert!(analysis.structure.test_dirs.contains(&"tests".to_string()));
    }

    #[test]
    fn create_context_file_writes_agents_md() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("pyproject.toml"),
            "[project]\nname = \"test\"\n",
        )
        .unwrap();

        let initializer = ProjectInitializer::new(dir.path());
        let path = initializer.create_context_file();

        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.contains("# "));
        assert!(content.contains("Language: python"));
        assert!(content.contains("Package Manager: pip"));
    }
}
