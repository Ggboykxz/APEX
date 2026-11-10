import React from "react"
import { render } from "ink"
import { TuiStoreProvider } from "./context/TuiStoreProvider.js"
import { ApexApp } from "./components/ApexApp.js"

render(
  React.createElement(TuiStoreProvider, null, React.createElement(ApexApp))
)
