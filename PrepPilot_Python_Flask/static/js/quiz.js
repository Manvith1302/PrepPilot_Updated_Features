const form = document.getElementById("quiz-form");
if (form) {
  const cards = [...document.querySelectorAll(".question-card")];
  const count = document.getElementById("answered-count");
  const fill = document.getElementById("progress-fill");
  const total = cards.length;
  function updateProgress() {
    const answered = cards.filter(card => card.querySelector("input:checked")).length;
    count.textContent = `${answered} of ${total} answered`;
    fill.style.width = `${answered / total * 100}%`;
  }
  document.addEventListener("change", updateProgress);
  let seconds = Number(form.dataset.duration);
  const timer = document.getElementById("timer");
  function tick() {
    const min = Math.floor(seconds / 60), sec = seconds % 60;
    timer.textContent = `${String(min).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
    if (seconds <= 60) timer.classList.add("urgent");
    if (seconds <= 0) { submitQuiz(); return; }
    seconds--;
  }
  tick(); const interval = setInterval(tick, 1000);
  let submitted = false;
  async function submitQuiz() {
    if (submitted) return;
    submitted = true; clearInterval(interval);
    const answers = {};
    cards.forEach(card => {
      const selected = card.querySelector("input:checked");
      if (selected) answers[card.dataset.question] = selected.value;
    });
    const response = await fetch("/submit-quiz", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({category: form.dataset.category, answers})
    });
    const data = await response.json();
    if (!response.ok) { alert(data.error || "Unable to submit test."); submitted = false; return; }
    document.getElementById("score-text").textContent = `${data.score} / ${data.total} · ${data.percentage}%`;
    document.getElementById("score-message").textContent = data.percentage >= 80 ? "Excellent work. Keep challenging yourself!" : "Good effort. Review, practice and try again!";
    document.getElementById("result-modal").classList.remove("hidden");
  }
  form.addEventListener("submit", event => {
    event.preventDefault();
    const unanswered = cards.filter(card => !card.querySelector("input:checked")).length;
    if (unanswered && !confirm(`${unanswered} question(s) are unanswered. Submit anyway?`)) return;
    submitQuiz();
  });
}
