// Global variables
const isAuthenticated = document.querySelector('meta[name="user-authenticated"]').content === "true"
let codeEditor
let currentMode = "review" // 'solution' or 'hints'

// Language templates
const languageTemplates = {
  python: `# Write your Python code here
def main():
    # Your solution goes here
    pass

if __name__ == "__main__":
    main()
`,
  cpp: `#include <bits/stdc++.h>
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
  // Fallback: get from cookie
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

// Initialize CodeMirror
function initializeCodeEditor() {
  console.log("Initializing CodeMirror...")
  const CodeMirror = window.CodeMirror // Declare CodeMirror variable
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

  // Set fixed height to prevent shrinking
  codeEditor.setSize(null, 400)
  codeEditor.setValue(languageTemplates.python)
  console.log("CodeMirror initialized successfully")
}

// Language handling
function setupLanguageSelector() {
  console.log("Setting up language selector...")
  const languageSelect = document.getElementById("language-select")
  const languageInput = document.getElementById("language-input")

  languageSelect.addEventListener("change", function () {
    const language = this.value
    languageInput.value = language

    // Update CodeMirror mode based on language
    if (language === "python") {
      codeEditor.setOption("mode", "text/x-python")
    } else if (language === "cpp" || language === "c") {
      codeEditor.setOption("mode", "text/x-c++src")
    } else if (language === "java") {
      codeEditor.setOption("mode", "text/x-java")
    }

    // Set template code if editor is empty or user confirms
    if (
      codeEditor.getValue().trim() === "" ||
      confirm("Change to " + language + " template? This will replace your current code.")
    ) {
      codeEditor.setValue(languageTemplates[language])
    }
  })

  // Set initial language value
  languageInput.value = languageSelect.value
  console.log("Language selector setup complete")
}

// Run Code functionality
function setupRunButton() {
  console.log("Setting up run button...")
  document.getElementById("run-btn").addEventListener("click", async function () {
    console.log("Run button clicked")
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
  console.log("Run button setup complete")
}

// Submit Solution functionality
function setupSubmitButton() {
  console.log("Setting up submit button...")
  document.getElementById("submit-btn").addEventListener("click", () => {
    console.log("Submit button clicked")
    if (!checkAuthentication()) return

    const code = codeEditor.getValue()
    const language = document.getElementById("language-select").value

    if (!code.trim()) {
      alert("Please write some code before submitting.")
      return
    }

    // Set form values
    document.getElementById("submit-code").value = code
    document.getElementById("submit-language").value = language

    // Submit the form
    document.getElementById("submit-form").submit()
  })
  console.log("Submit button setup complete")
}

// AI Assist functionality
function setupAIAssist() {
  console.log("Setting up AI assist...")

  // Mode switching buttons
  const reviewBtn = document.getElementById("ai-review-btn")
  const feedbackBtn = document.getElementById("ai-feedback-btn")

  if (reviewBtn) {
    reviewBtn.addEventListener("click", function () {
      console.log("Review mode selected")
      if (currentMode !== "review") {
        currentMode = "review"
        this.classList.add("active")
        feedbackBtn.classList.remove("active")
        getAIAssistance()
      }
    })
  }

  if (feedbackBtn) {
    feedbackBtn.addEventListener("click", function () {
      console.log("Feedback mode selected")
      if (currentMode !== "feedback") {
        currentMode = "feedback"
        this.classList.add("active")
        reviewBtn.classList.remove("active")
        getAIAssistance()
      }
    })
  }

  // Main assist button
  const assistBtn = document.getElementById("assist-btn")
  if (assistBtn) {
    assistBtn.addEventListener("click", () => {
      console.log("AI Review button clicked")
      if (!checkAuthentication()) return

      // Check if user has written any code
      const userCode = codeEditor.getValue().trim()
      if (!userCode) {
        alert("Please write some code first before requesting a review!")
        return
      }

      const aiAssistance = document.getElementById("ai-assistance")
      if (aiAssistance) {
        // Show the assistance panel
        aiAssistance.style.display = "block"
        console.log("AI assistance panel shown")

        // Get AI assistance
        getAIAssistance()
      } else {
        console.error("AI assistance panel not found")
      }
    })
    console.log("AI assist button listener added")
  } else {
    console.error("AI assist button not found")
  }

  // Close button
  const closeBtn = document.getElementById("close-assist")
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      console.log("Closing AI assistance")
      const aiAssistance = document.getElementById("ai-assistance")
      if (aiAssistance) {
        aiAssistance.style.display = "none"
      }
    })
    console.log("Close button listener added")
  } else {
    console.error("Close assist button not found")
  }

  console.log("AI assist setup complete")
}

async function getAIAssistance() {
  console.log("Getting AI assistance...")
  const assistBtn = document.getElementById("assist-btn")
  const aiContent = document.getElementById("ai-content")
  const language = document.getElementById("language-select").value
  const problemId = document.querySelector('meta[name="problem-id"]').content
  const problemTitle = document.querySelector('meta[name="problem-title"]').content
  const problemDescription = document.querySelector('meta[name="problem-description"]').content

  console.log("AI request data:", {
    problemId,
    problemTitle,
    language,
    mode: currentMode,
  })

  // Show loading state
  if (assistBtn) assistBtn.disabled = true
  if (aiContent) {
    aiContent.innerHTML = '<div class="loading-spinner">Getting AI assistance...</div>'
  }

  try {
    const response = await fetch(`/problems/${problemId}/assist/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        problem_id: problemId,
        problem_title: problemTitle,
        problem_description: problemDescription,
        language: language,
        mode: currentMode,
        user_code: codeEditor.getValue(), // Add user's code
      }),
    })

    console.log("AI response status:", response.status)
    const result = await response.json()
    console.log("AI response:", result)

    if (result.success) {
      if (aiContent) {
        aiContent.innerHTML = result.assistance
        setupCodeInteractions()
        console.log("AI assistance loaded successfully")
      }
    } else {
      const errorMsg =
        '<div class="ai-hint"><h4>Error</h4><p>' +
        (result.error || "Failed to get AI assistance. Please try again.") +
        "</p></div>"
      if (aiContent) {
        aiContent.innerHTML = errorMsg
      }
      console.error("AI assistance error:", result.error)
    }
  } catch (error) {
    console.error("Network error:", error)
    if (aiContent) {
      aiContent.innerHTML = '<div class="ai-hint"><h4>Error</h4><p>Network error: ' + error.message + "</p></div>"
    }
  } finally {
    if (assistBtn) assistBtn.disabled = false
  }
}

function setupCodeInteractions() {
  console.log("Setting up code interactions...")
  const aiContent = document.getElementById("ai-content")

  if (!aiContent) return

  // Copy buttons
  const copyButtons = aiContent.querySelectorAll(".ai-code-copy")
  copyButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const codeBlock = this.closest(".ai-code").querySelector("pre")
      const code = codeBlock.textContent

      navigator.clipboard.writeText(code).then(() => {
        const originalText = this.textContent
        this.textContent = "Copied!"
        setTimeout(() => {
          this.textContent = originalText
        }, 2000)
      })
    })
  })

  // Use solution buttons
  const useSolutionButtons = aiContent.querySelectorAll(".use-solution-btn")
  useSolutionButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const codeBlock = this.closest(".ai-code").querySelector("pre")
      const code = codeBlock.textContent

      if (codeEditor) {
        codeEditor.setValue(code)
        document.getElementById("ai-assistance").style.display = "none"
      }
    })
  })

  console.log("Code interactions setup complete")
}

// Initialize everything when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM loaded, initializing...")

  // Wait a bit for CodeMirror to be available
  setTimeout(() => {
    try {
      initializeCodeEditor()
      setupLanguageSelector()
      setupRunButton()
      setupSubmitButton()
      setupAIAssist()
      console.log("All components initialized successfully")
    } catch (error) {
      console.error("Error during initialization:", error)
    }
  }, 100)
})
