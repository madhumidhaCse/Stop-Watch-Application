const display = document.getElementById("display");
const startBtn = document.getElementById("startBtn");
const lapBtn = document.getElementById("lapBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resetBtn = document.getElementById("resetBtn");
const saveBtn = document.getElementById("saveBtn");
const lapTable = document.getElementById("lapTable");
const sessionName = document.getElementById("sessionName");
const message = document.getElementById("message");
const sessionsList = document.getElementById("sessionsList");
const refreshBtn = document.getElementById("refreshBtn");
const chartPanel = document.getElementById("chartPanel");
const chartImage = document.getElementById("chartImage");

let running = false;
let hasStarted = false;
let elapsedBeforeStart = 0;
let startTimestamp = 0;
let animationFrame = null;
let previousLapTime = 0;
let laps = [];
let saved = false;

function getElapsedTime() {
    return running
        ? elapsedBeforeStart + (performance.now() - startTimestamp) / 1000
        : elapsedBeforeStart;
}

function formatTime(seconds) {
    const totalMilliseconds = Math.floor(seconds * 1000);
    const hours = Math.floor(totalMilliseconds / 3600000);
    const minutes = Math.floor((totalMilliseconds % 3600000) / 60000);
    const remainingSeconds = Math.floor((totalMilliseconds % 60000) / 1000);
    const milliseconds = totalMilliseconds % 1000;
    return String(hours).padStart(2, "0") + ":" +
        String(minutes).padStart(2, "0") + ":" +
        String(remainingSeconds).padStart(2, "0") + "." +
        String(milliseconds).padStart(3, "0");
}

function updateDisplay() {
    display.textContent = formatTime(getElapsedTime());
    if (running) animationFrame = requestAnimationFrame(updateDisplay);
}

function updateButtons() {
    startBtn.disabled = running;
    lapBtn.disabled = !running;
    pauseBtn.disabled = !running;
    saveBtn.disabled = !hasStarted || running || saved;
}

startBtn.addEventListener("click", () => {
    if (running) return;
    running = true;
    hasStarted = true;
    saved = false;
    startTimestamp = performance.now();
    message.textContent = "";
    cancelAnimationFrame(animationFrame);
    updateDisplay();
    updateButtons();
});

pauseBtn.addEventListener("click", () => {
    if (!running) return;
    elapsedBeforeStart = getElapsedTime();
    running = false;
    cancelAnimationFrame(animationFrame);
    display.textContent = formatTime(elapsedBeforeStart);
    updateButtons();
    message.textContent = "Stopwatch paused.";
});

lapBtn.addEventListener("click", () => {
    if (!running) return;
    const totalTime = getElapsedTime();
    const lapTime = totalTime - previousLapTime;
    laps.push({ lap_number: laps.length + 1, lap_time: lapTime, total_time: totalTime });
    previousLapTime = totalTime;
    renderLaps();
    saved = false;
    updateButtons();
    message.textContent = "Lap " + laps.length + " recorded.";
});

function renderLaps() {
    lapTable.replaceChildren();
    if (laps.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 3;
        cell.textContent = "No laps recorded yet.";
        row.appendChild(cell);
        lapTable.appendChild(row);
        return;
    }
    [...laps].reverse().forEach(lap => {
        const row = document.createElement("tr");
        const numberCell = document.createElement("td");
        const durationCell = document.createElement("td");
        const totalCell = document.createElement("td");
        numberCell.textContent = lap.lap_number;
        durationCell.textContent = formatTime(lap.lap_time);
        totalCell.textContent = formatTime(lap.total_time);
        row.append(numberCell, durationCell, totalCell);
        lapTable.appendChild(row);
    });
}

resetBtn.addEventListener("click", () => {
    running = false;
    hasStarted = false;
    elapsedBeforeStart = 0;
    previousLapTime = 0;
    laps = [];
    saved = false;
    cancelAnimationFrame(animationFrame);
    display.textContent = "00:00:00.000";
    renderLaps();
    updateButtons();
    message.textContent = "Stopwatch reset.";
    chartPanel.hidden = true;
});

saveBtn.addEventListener("click", async () => {
    if (!hasStarted || running || saved) return;
    const totalTime = getElapsedTime();
    if (totalTime <= 0) {
        message.textContent = "Run the stopwatch before saving.";
        return;
    }
    const name = sessionName.value.trim();
    if (!name) {
        message.textContent = "Please enter a session name.";
        sessionName.focus();
        return;
    }
    saveBtn.disabled = true;
    message.textContent = "Saving session...";
    try {
        const response = await fetch("/api/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                total_time: totalTime,
                laps: laps.map(lap => ({
                    lap_time: lap.lap_time,
                    total_time: lap.total_time
                }))
            })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not save session.");
        saved = true;
        updateButtons();
        message.textContent = "Session saved successfully!";
        await loadSessions();
    } catch (error) {
        message.textContent = error.message;
        updateButtons();
    }
});

async function loadSessions() {
    sessionsList.textContent = "Loading sessions...";
    try {
        const response = await fetch("/api/sessions");
        if (!response.ok) throw new Error("Could not load sessions.");
        const sessions = await response.json();
        sessionsList.replaceChildren();
        if (sessions.length === 0) {
            sessionsList.textContent = "No saved sessions yet.";
            return;
        }
        sessions.forEach(session => {
            const item = document.createElement("article");
            item.className = "session-item";
            const title = document.createElement("h3");
            title.textContent = session.name;
            const duration = document.createElement("p");
            duration.textContent = "Total time: " + session.formatted_time;
            const lapCount = document.createElement("p");
            lapCount.textContent = "Laps: " + session.lap_count;
            const date = document.createElement("p");
            date.textContent = "Saved: " + session.created_at;
            const actions = document.createElement("div");
            actions.className = "session-actions";

            const detailsLink = document.createElement("a");
            detailsLink.className = "action-link";
            detailsLink.href = "#";
            detailsLink.textContent = "View Laps";
            detailsLink.addEventListener("click", event => {
                event.preventDefault();
                viewSession(session.id);
            });
            actions.appendChild(detailsLink);

            const csvLink = document.createElement("a");
            csvLink.className = "action-link";
            csvLink.href = "/api/sessions/" + session.id + "/csv";
            csvLink.textContent = "Export CSV";
            actions.appendChild(csvLink);

            if (Number(session.lap_count) > 0) {
                const chartLink = document.createElement("a");
                chartLink.className = "action-link";
                chartLink.href = "#chartPanel";
                chartLink.textContent = "View Chart";
                chartLink.addEventListener("click", event => {
                    event.preventDefault();
                    chartImage.src = "/api/sessions/" + session.id + "/chart?time=" + Date.now();
                    chartPanel.hidden = false;
                    chartPanel.scrollIntoView({ behavior: "smooth" });
                });
                actions.appendChild(chartLink);
            }
            item.append(title, duration, lapCount, date, actions);
            sessionsList.appendChild(item);
        });
    } catch (error) {
        sessionsList.textContent = error.message;
    }
}

async function viewSession(sessionId) {
    try {
        const response = await fetch("/api/sessions/" + sessionId);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load session.");
        lapTable.replaceChildren();
        if (data.laps.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 3;
            cell.textContent = "No laps in this session.";
            row.appendChild(cell);
            lapTable.appendChild(row);
        } else {
            data.laps.forEach(lap => {
                const row = document.createElement("tr");
                const numberCell = document.createElement("td");
                const durationCell = document.createElement("td");
                const totalCell = document.createElement("td");
                numberCell.textContent = lap.lap_number;
                durationCell.textContent = lap.formatted_lap_time;
                totalCell.textContent = lap.formatted_total_time;
                row.append(numberCell, durationCell, totalCell);
                lapTable.appendChild(row);
            });
        }
        message.textContent = "Viewing saved session: " + data.name;
        document.querySelectorAll(".panel")[0].scrollIntoView({ behavior: "smooth" });
    } catch (error) {
        message.textContent = error.message;
    }
}

refreshBtn.addEventListener("click", loadSessions);
renderLaps();
updateButtons();
loadSessions();
