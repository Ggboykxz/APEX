/**
 * CommandPalette — composant TUI Ink (APEX).
 * Palette de commandes slash comme OpenCode : filtre + sélection clavier.
 * État local pur, rendu contrôlé par ApexApp.
 */

import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';

export interface PaletteItem {
  id: string;
  label: string;
  description?: string;
}

interface CommandPaletteProps {
  items: PaletteItem[];
  visible: boolean;
  onSelect: (item: PaletteItem) => void;
  onClose: () => void;
}

export function CommandPalette({ items, visible, onSelect, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);

  const filtered = query.trim()
    ? items.filter((i) =>
        i.label.toLowerCase().includes(query.toLowerCase()) ||
        (i.description ?? '').toLowerCase().includes(query.toLowerCase()),
      )
    : items;

  // Garder le curseur dans les bornes
  const safeCursor = Math.min(cursor, Math.max(0, filtered.length - 1));

  useInput((input, key) => {
    if (!visible) return;
    if (key.escape) {
      onClose();
      return;
    }
    if (key.upArrow) {
      setCursor((c) => Math.max(0, c - 1));
      return;
    }
    if (key.downArrow) {
      setCursor((c) => Math.min(filtered.length - 1, c + 1));
      return;
    }
    if (key.return) {
      if (filtered[safeCursor]) onSelect(filtered[safeCursor]);
      return;
    }
    if (key.backspace) {
      setQuery((q) => q.slice(0, -1));
      return;
    }
    // Saisie de caractère (une seule lettre à la fois)
    if (/^[\x20-\x7E]$/.test(input)) {
      setQuery((q) => q + input);
    }
  });

  if (!visible) return null;

  return (
    <Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1} width={60}>
      <Text bold color="cyan">  </Text>
      <Text>{query || 'Tapez une commande…'}</Text>
      <Box flexDirection="column" marginTop={1}>
        {filtered.length === 0 && <Text color="gray">Aucun résultat</Text>}
        {filtered.slice(0, 10).map((item, idx) => (
          <Box key={item.id}>
            <Text color={idx === safeCursor ? 'cyan' : 'gray'}>
              {idx === safeCursor ? '› ' : '  '}
              {item.label}
              {item.description ? ` — ${item.description}` : ''}
            </Text>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
