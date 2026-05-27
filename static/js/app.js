const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

const savedTheme = localStorage.getItem("medflow-theme");
if (savedTheme === "dark") document.body.classList.add("dark");

$("#themeToggle")?.addEventListener("click", () => {
    document.body.classList.toggle("dark");
    localStorage.setItem("medflow-theme", document.body.classList.contains("dark") ? "dark" : "light");
});

$("#settingsTheme")?.addEventListener("change", (event) => {
    document.body.classList.toggle("dark", event.target.checked);
    localStorage.setItem("medflow-theme", event.target.checked ? "dark" : "light");
});

$("#sidebarToggle")?.addEventListener("click", () => $("#sidebar")?.classList.toggle("open"));

$$("[data-modal]").forEach((button) => {
    button.addEventListener("click", () => document.getElementById(button.dataset.modal)?.classList.add("open"));
});

$$(".close-modal").forEach((button) => {
    button.addEventListener("click", () => button.closest(".modal")?.classList.remove("open"));
});

$$(".modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
        if (event.target === modal) modal.classList.remove("open");
    });
});

$$(".click-row").forEach((row) => {
    row.addEventListener("click", (event) => {
        if (event.target.closest("a, button, form, input, select")) return;
        window.location.href = row.dataset.href;
    });
});

$$(".counter").forEach((counter) => {
    const end = Number(counter.dataset.count || 0);
    let frame = 0;
    const tick = () => {
        frame += 1;
        counter.textContent = Math.round((end * frame) / 38);
        if (frame < 38) requestAnimationFrame(tick);
        else counter.textContent = end;
    };
    tick();
});

const chartDefaults = () => {
    Chart.defaults.color = getComputedStyle(document.body).getPropertyValue("--muted").trim();
    Chart.defaults.borderColor = getComputedStyle(document.body).getPropertyValue("--line").trim();
    Chart.defaults.font.family = "Inter, system-ui, sans-serif";
};

const makeGradient = (ctx) => {
    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, "rgba(23, 199, 213, .45)");
    gradient.addColorStop(1, "rgba(23, 199, 213, .02)");
    return gradient;
};

const renderCharts = async () => {
    if (!window.Chart) return;
    chartDefaults();
    let data = { patients: [18, 25, 32, 38, 44, 58, 67], appointments: [12, 19, 15, 28, 24, 31, 27], tests: { CBC: 34, "Blood Sugar": 26, Urine: 18, Thyroid: 14, Lipid: 22 }, workload: [72, 58, 81, 63] };
    try {
        const response = await fetch("/api/chart-data");
        if (response.ok) data = await response.json();
    } catch (error) {
        console.info("Using bundled chart data.");
    }

    const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const patientCanvas = $("#patientChart") || $("#growthChart");
    if (patientCanvas) {
        new Chart(patientCanvas, {
            type: "line",
            data: { labels, datasets: [{ label: "Patients", data: data.patients, borderColor: "#17c7d5", backgroundColor: makeGradient(patientCanvas.getContext("2d")), tension: .42, fill: true, pointRadius: 4 }] },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    }
    const appointmentCanvas = $("#appointmentChart");
    if (appointmentCanvas) {
        new Chart(appointmentCanvas, {
            type: "bar",
            data: { labels, datasets: [{ label: "Appointments", data: data.appointments, borderRadius: 10, backgroundColor: ["#3478f6", "#17c7d5", "#2ecf8f", "#7bdff2", "#79b8ff", "#20d0a6", "#6ea8fe"] }] },
            options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    }
    const testCanvas = $("#testChart");
    if (testCanvas) {
        new Chart(testCanvas, {
            type: "doughnut",
            data: { labels: Object.keys(data.tests), datasets: [{ data: Object.values(data.tests), backgroundColor: ["#3478f6", "#17c7d5", "#2ecf8f", "#ffcf66", "#ff8a8a"], borderWidth: 0 }] },
            options: { cutout: "68%" }
        });
    }
    const diseaseCanvas = $("#diseaseChart");
    if (diseaseCanvas) {
        new Chart(diseaseCanvas, {
            type: "radar",
            data: { labels: ["Fever", "Diabetes", "Thyroid", "ENT", "Lipid"], datasets: [{ data: [38, 29, 21, 18, 24], backgroundColor: "rgba(46, 207, 143, .22)", borderColor: "#2ecf8f" }] },
            options: { plugins: { legend: { display: false } } }
        });
    }
    const workloadCanvas = $("#workloadChart");
    if (workloadCanvas) {
        new Chart(workloadCanvas, {
            type: "bar",
            data: { labels: ["Hematology", "Biochem", "Pathology", "Urine"], datasets: [{ data: data.workload, backgroundColor: "#17c7d5", borderRadius: 10 }] },
            options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, max: 100 } } }
        });
    }
};

renderCharts();
