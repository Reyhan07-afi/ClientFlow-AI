document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const analyzeButton = document.querySelector("#analyze-ticket");
  if (!analyzeButton) return;
  analyzeButton.addEventListener("click", async () => {
    const result = document.querySelector("#ai-result");
    result.textContent = "Analyzing ticket…";
    analyzeButton.disabled = true;
    try {
      const body = new URLSearchParams({
        subject: document.querySelector("#ticket-subject").value,
        description: document.querySelector("#ticket-description").value,
      });
      const response = await fetch("/tickets/analyze", {
        method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Analysis failed.");
      document.querySelector("#ticket-category").value = data.category || "General";
      if (data.priority) {
        const priority = [...document.querySelector("#ticket-priority").options].find((option) => option.value.toLowerCase() === data.priority.toLowerCase());
        if (priority) priority.selected = true;
      }
      result.className = "ai-output";
      result.textContent = `Summary: ${data.summary} · Next action: ${data.next_action}`;
    } catch (error) {
      result.className = "";
      result.textContent = error.message;
    } finally {
      analyzeButton.disabled = false;
    }
  });
});
