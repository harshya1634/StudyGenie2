async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let msg = "Request failed";
    try {
      const data = await res.json();
      msg = data.error || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

document.addEventListener("DOMContentLoaded", async () => {
  const el = document.getElementById("calendar");
  const events = await api("/api/events");

  const calendar = new FullCalendar.Calendar(el, {
    initialView: "dayGridMonth",
    height: "auto",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,timeGridWeek,timeGridDay",
    },
    events,
    dateClick: async (info) => {
      const title = window.prompt("Event title:");
      if (!title) return;
      const created = await api("/api/events", {
        method: "POST",
        body: JSON.stringify({ title, start: info.dateStr }),
      });
      calendar.addEvent({ id: created.id, title, start: info.dateStr });
    },
    eventClick: async (info) => {
      const ok = window.confirm(`Delete "${info.event.title}"?`);
      if (!ok) return;
      await api(`/api/events/${info.event.id}`, { method: "DELETE" });
      info.event.remove();
    },
  });

  calendar.render();
});

