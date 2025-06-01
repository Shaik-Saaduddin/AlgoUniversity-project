// AI Assist functionality
let currentMode = "" // Declare currentMode variable
let codeEditor // Declare codeEditor variable

function setupAIAssist() {
  // Mode switching
  document.getElementById("ai-solution-btn").addEventListener("click", function () {
    if (currentMode !== "solution") {
      currentMode = "solution"
      this.classList.add("active")
      document.getElementById("ai-hint-btn").classList.remove("active")
      getAIAssistance()
    }
  })

  document.getElementById("ai-hint-btn").addEventListener("click", function () {
    if (currentMode !== "hints") {
      currentMode = "hints"
      this.classList.add("active")
      document.getElementById("ai-solution-btn").classList.remove("active")
      getAIAssistance()
    }
  })

  // Main assist button
  document.getElementById("assist-btn").addEventListener("click", () => {
    if (!checkAuthentication()) return

    const aiAssistance = document.getElementById("ai-assistance")
    aiAssistance.style.display = "block"
    getAIAssistance()
  })

  // Close button
  document.getElementById("close-assist").addEventListener("click", () => {
    document.getElementById("ai-assistance").style.display = "none"
  })
}

async function getAIAssistance() {
  const assistBtn = document.getElementById("assist-btn")
  const aiContent = document.getElementById("ai-content")
  const language = document.getElementById("language-select").value
  const problemId = document.querySelector('meta[name="problem-id"]').content
  const problemTitle = document.querySelector('meta[name="problem-title"]').content
  const problemDescription = document.querySelector('meta[name="problem-description"]').content

  // Show loading state
  assistBtn.disabled = true
  aiContent.innerHTML = '<div class="loading-spinner">Getting AI assistance...</div>'

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
      }),
    })

    const result = await response.json()

    if (result.success) {
      aiContent.innerHTML = result.assistance
      setupCodeInteractions()
    } else {
      const errorMsg =
        '<div class="ai-hint"><h4>Error</h4><p>' +
        (result.error || "Failed to get AI assistance. Please try again.") +
        "</p></div>"
      aiContent.innerHTML = errorMsg
    }
  } catch (error) {
    aiContent.innerHTML = '<div class="ai-hint"><h4>Error</h4><p>Network error: ' + error.message + "</p></div>"
  } finally {
    assistBtn.disabled = false
  }
}

function setupCodeInteractions() {
  const aiContent = document.getElementById("ai-content")

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

      codeEditor.setValue(code)
      document.getElementById("ai-assistance").style.display = "none"
    })
  })
}

function checkAuthentication() {
  // Placeholder for authentication check logic
  return true // Assume user is authenticated for now
}

function getCSRFToken() {
  // Placeholder for CSRF token retrieval logic
  return "csrf_token_here" // Replace with actual CSRF token retrieval
}

// Initialize AI assist when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  codeEditor = document.getElementById("code-editor") // Initialize codeEditor
  setupAIAssist()
})
