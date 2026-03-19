---
name: use-windows-powershell
description: 'Use Windows PowerShell (powershell.exe) when pwsh.exe (PowerShell Core) is not available. Fixes "pwsh.exe not recognized" errors. Use when shell commands fail because PowerShell Core is missing, when running on Windows without PowerShell 6+, or when any tool requires a shell and pwsh is absent.'
argument-hint: Command to run in Windows PowerShell
---

# Use Windows PowerShell (powershell.exe)

## Problem
The Copilot CLI shell tool requires `pwsh.exe`. If missing, every shell command fails: