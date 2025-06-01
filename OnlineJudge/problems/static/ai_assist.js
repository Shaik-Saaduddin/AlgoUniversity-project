document.addEventListener("DOMContentLoaded", () => {
  // Check if we're on a problem page
  const problemContainer = document.querySelector(".problem-container")
  if (!problemContainer) return

  // Get problem ID from the URL
  const pathParts = window.location.pathname.split("/")
  const problemId = pathParts[pathParts.length - 1]

  // Create the AI assist button
  const assistButton = document.createElement("button")
  assistButton.id = "ai-assist-btn"
  assistButton.className = "btn btn-primary"
  assistButton.innerHTML = "🤖 AI Assist"
  assistButton.style.marginLeft = "10px"

  // Find where to insert the button (next to the language selector)
  const languageSelector = document.querySelector(".language-selector")
  if (languageSelector) {
    languageSelector.parentNode.insertBefore(assistButton, languageSelector.nextSibling)
  } else {
    // Fallback - add to the top of the problem description
    const problemDescription = document.querySelector(".problem-description")
    if (problemDescription) {
      problemDescription.parentNode.insertBefore(assistButton, problemDescription)
    }
  }

  // Create the AI assistance panel (initially hidden)
  const assistPanel = document.createElement("div")
  assistPanel.id = "ai-assist-panel"
  assistPanel.className = "ai-assist-panel"
  assistPanel.style.display = "none"
  assistPanel.innerHTML = `
        <div class="ai-assist-header">
            <h3>AI Assistance</h3>
            <button id="close-assist-panel" class="close-btn">&times;</button>
        </div>
        <div id="ai-assist-content" class="ai-assist-content">
            <div class="ai-loading">Loading AI assistance...</div>
        </div>
    `

  // Add the panel to the page
  document.body.appendChild(assistPanel)

  // Add CSS for the AI assist panel
  const style = document.createElement("style")
  style.textContent = `
        .ai-assist-panel {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .ai-assist-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        
        .ai-assist-header h3 {
            margin: 0;
            font-size: 18px;
            color: #343a40;
        }
        
        .close-btn {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #6c757d;
        }
        
        .ai-assist-content {
            padding: 20px;
            overflow-y: auto;
            flex-grow: 1;
        }
        
        .ai-loading {
            text-align: center;
            padding: 20px;
            color: #6c757d;
        }
        
        .ai-hint {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }
        
        .ai-hint h4 {
            margin-top: 0;
            color: #343a40;
        }
    `
  document.head.appendChild(style)

  // Handle button click
  assistButton.addEventListener("click", () => {
    assistPanel.style.display = "flex"

    // Get the problem description
    const problemDescriptionElement = document.querySelector(".problem-description")
    const problemDescription = problemDescriptionElement ? problemDescriptionElement.textContent : ""

    // Get CSRF token
    function getCookie(name) {
      let cookieValue = null
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";")
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim()
          if (cookie.substring(0, name.length + 1) === name + "=") {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
            break
          }
        }
      }
      return cookieValue
    }
    const csrftoken = getCookie("csrftoken")

    // Fetch AI assistance
    fetch(`/problems/${problemId}/assist/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
      },
      body: JSON.stringify({
        problem_description: problemDescription,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        const assistContent = document.getElementById("ai-assist-content")
        if (data.success) {
          assistContent.innerHTML = data.assistance
        } else {
          assistContent.innerHTML = `
                    <div class="ai-hint">
                        <h4>Error</h4>
                        <p>Sorry, there was an error getting AI assistance: ${data.error}</p>
                    </div>
                `
        }
      })
      .catch((error) => {
        const assistContent = document.getElementById("ai-assist-content")
        assistContent.innerHTML = `
                <div class="ai-hint">
                    <h4>Error</h4>
                    <p>Sorry, there was an error connecting to the AI service. Please try again later.</p>
                </div>
            `
        console.error("Error:", error)
      })
  })

  // Close button functionality
  document.getElementById("close-assist-panel").addEventListener("click", () => {
    assistPanel.style.display = "none"
  })

  // Close when clicking outside
  window.addEventListener("click", (event) => {
    if (event.target === assistPanel) {
      assistPanel.style.display = "none"
    }
  })
})
