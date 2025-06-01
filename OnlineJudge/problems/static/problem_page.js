// Global variables
const isAuthenticated = document.querySelector('meta[name="user-authenticated"]').content === "true"
let codeEditor
const currentMode = "solution"

// Language templates
const languageTemplates = {
  python: `# Write your Python code here
def main():
    # Your solution goes here
    pass

if __name__ == "__main__":
    main()
`,
  cpp: `#include <bits/stc++.h>
using namespace std;

int main() {
    // Write your C++ code here
    
    return 0;
}
`,
  java: `import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        
        // Write your Java code here
        
        scanner.close();
    }
}
`,
  c: `#include <stdio.h>
#include <stdlib.h>

int main() {
    // Write your C code here
    
    return 0;
}
`,
}

// Utility functions
function getCSRFToken() {
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")
  if (csrfToken) {
    return csrfToken.value
  }
  const cookies = document.cookie.split(";")
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=")
    if (name === "csrftoken") {
      return value
    }
  }
  return ""
}

function checkAuthentication() {
  if (!isAuthenticated) {
    window.location.href = "/auth/login/?next=" + window.location.pathname
    return false
  }
  return true
}

// CodeMirror library import
const CodeMirror = window.CodeMirror

// Initialize CodeMirror
function initializeCodeEditor() {
  codeEditor = CodeMirror.fromTextArea(document.getElementById("code-editor"), {
    lineNumbers: true,
    mode: "text/x-python",
    theme: "dracula",
    indentUnit: 4,
    smartIndent: true,
    tabSize: 4,
    indentWithTabs: false,
    lineWrapping: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    styleActiveLine: true,
    foldGutter: true,
    gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
  })

  codeEditor.setSize(null, 400)
  codeEditor.setValue(languageTemplates.python)
}

// Language handling
function setupLanguageSelector() {
  const languageSelect = document.getElementById("language-select")
  const languageInput = document.getElementById("language-input")

  languageSelect.addEventListener("change", function () {
    const language = this.value
    languageInput.value = language

    // Update CodeMirror mode
    const modeMap = {
      python: "text/x-python",
      cpp: "text/x-c++src",
      c: "text/x-c++src",
      java: "text/x-java",
    }

    codeEditor.setOption("mode", modeMap[language])

    // Set template code
    if (
      codeEditor.getValue().trim() === "" ||
      confirm("Change to " + language + " template? This will replace your current code.")
    ) {
      codeEditor.setValue(languageTemplates[language])
    }
  })

  languageInput.value = languageSelect.value
}

// Run code functionality
function setupRunButton() {
  document.getElementById("run-btn").addEventListener("click", async function () {
    if (!checkAuthentication()) return

    const code = codeEditor.getValue()
    const language = document.getElementById("language-select").value
    const customInput = document.getElementById("custom-input").value
    const outputContainer = document.getElementById("output-container")
    const executionInfo = document.getElementById("execution-info")
    

    if (!code.trim()) {
      outputContainer.textContent = "Error: No code provided"
      outputContainer.className = "output-container error"
      return
    }

    // Show loading state
    this.disabled = true
    this.textContent = "Running..."
    outputContainer.textContent = "Executing code..."
    outputContainer.className = "output-container loading"
    executionInfo.textContent = ""

    try {
      const response = await fetch("/compiler/run/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({
          code: code,
          language: language,
          input: customInput,
        }),
      })

      const result = await response.json()

      if (result.success) {
        if (result.error) {
          outputContainer.textContent = result.error
          outputContainer.className = "output-container error"
        } else {
          outputContainer.textContent = result.output || "(No output)"
          outputContainer.className = "output-container success"
        }

        if (result.execution_time) {
          executionInfo.textContent = `Execution time: ${result.execution_time.toFixed(3)}s`
        }
      } else {
        outputContainer.textContent = result.error || "An error occurred"
        outputContainer.className = "output-container error"
      }
    } catch (error) {
      outputContainer.textContent = "Network error: " + error.message
      outputContainer.className = "output-container error"
    } finally {
      this.disabled = false
      this.textContent = "Run Code"
    }
  })
}

// Submit solution functionality
function setupSubmitButton() {
  document.getElementById("submit-btn").addEventListener("click", () => {
    if (!checkAuthentication()) return

    const code = codeEditor.getValue()
    const language = document.getElementById("language-select").value

    if (!code.trim()) {
      alert("Please write some code before submitting.")
      return
    }

    document.getElementById("submit-code").value = code
    document.getElementById("submit-language").value = language
    document.getElementById("submit-form").submit()
  })
}

// Initialize everything when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  initializeCodeEditor()
  setupLanguageSelector()
  setupRunButton()
  setupSubmitButton()
})
