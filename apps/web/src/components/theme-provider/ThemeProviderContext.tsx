import { createContext } from "react";
import type { ThemeProviderState } from "./theme-provider";
import { initialState } from "./initialState";


export const ThemeProviderContext = createContext<ThemeProviderState>(initialState);
