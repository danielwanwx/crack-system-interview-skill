document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  const target = document.querySelector(button.dataset.copy);
  if (!target) return;
  await navigator.clipboard.writeText(target.textContent.trim());
  const previous = button.textContent;
  button.textContent = "已复制";
  setTimeout(() => { button.textContent = previous; }, 1400);
});
