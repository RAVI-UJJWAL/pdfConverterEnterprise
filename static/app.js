console.log("APP.JS LOADED");

// ================= DOM =================
const fileInput = document.getElementById("fileInput");
const convertBtn = document.getElementById("convertBtn");
const fileList = document.getElementById("fileList");
const spinner = document.getElementById("spinner");
const message = document.getElementById("message");
const cancelBtn = document.getElementById("cancelBtn");
const downloadAllBtn = document.getElementById("downloadAllBtn");
const resetBtn = document.getElementById("resetBtn");
const themeToggle = document.getElementById("themeToggle");
const dropZone = document.getElementById("drop-zone");

let files = [];
let jobId = null;
let poller = null;

// ================= THEME =================
themeToggle.addEventListener("click", () => {
    const theme = document.documentElement.getAttribute("data-theme");
    const newTheme = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
});

const savedTheme = localStorage.getItem("theme");
if (savedTheme) document.documentElement.setAttribute("data-theme", savedTheme);

// ================= DRAG & DROP =================
dropZone.addEventListener("dragover", e => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    addFiles([...e.dataTransfer.files]);
});

// ================= FILE INPUT =================
fileInput.addEventListener("change", () => addFiles([...fileInput.files]));

// ================= ADD FILES =================
function addFiles(newFiles) {
    files = files.concat(newFiles);
    renderFiles();
    convertBtn.disabled = files.filter(Boolean).length === 0;
    resetBtn.classList.remove("hidden");
}

// ================= RENDER FILES =================
function renderFiles() {
    fileList.innerHTML = "";

    files.forEach((f, i) => {
        if (!f) return;

        const li = document.createElement("li");
        li.className = "file-item";
        li.innerHTML = `
            <strong>${f.name}</strong>
            <div class="progress-bar">
                <div class="progress" id="progress-${i}"></div>
            </div>
            <div class="actions">
                <button class="download-btn" id="download-${i}" disabled>⬇ Download</button>
                <button class="cancel-file-btn" id="cancel-${i}">✖ Cancel</button>
            </div>
        `;
        fileList.appendChild(li);

        document.getElementById(`cancel-${i}`).onclick = () => {
            files[i] = null;
            renderFiles();
            convertBtn.disabled = files.filter(Boolean).length === 0;
        };
    });

    if (files.filter(Boolean).length > 1) {
        downloadAllBtn.classList.remove("hidden");
        downloadAllBtn.disabled = true;
    } else {
        downloadAllBtn.classList.add("hidden");
    }
}

// ================= CONVERT =================
convertBtn.addEventListener("click", async () => {
    if (!files.some(f => f)) return;

    convertBtn.disabled = true;
    cancelBtn.classList.remove("hidden");
    spinner.classList.remove("hidden");
    message.innerText = "Converting files...";
    message.style.color = "green";

    const formData = new FormData();
    files.forEach(f => f && formData.append("files", f));

    try {
        const res = await fetch("/api/convert", { method: "POST", body: formData });
        const data = await res.json();
        jobId = data.job_id;
        startPolling();
    } catch (e) {
        message.innerText = "Backend error";
        message.style.color = "red";
        convertBtn.disabled = false;
        cancelBtn.classList.add("hidden");
        spinner.classList.add("hidden");
    }
});

// ================= POLLING =================
function startPolling() {
    poller = setInterval(async () => {
        try {
            const res = await fetch(`/api/status/${jobId}`);
            const job = await res.json();

            job.files.forEach((f, i) => {
                const bar = document.getElementById(`progress-${i}`);
                const btn = document.getElementById(`download-${i}`);

                if (bar && f.progress !== undefined)
                    bar.style.width = `${f.progress}%`;

                if (btn && f.status === "done") {
                    btn.disabled = false;
                    btn.onclick = () => window.open(f.download_url, "_blank");
                }
            });

            if (job.status === "done") {
                clearInterval(poller);
                spinner.classList.add("hidden");
                cancelBtn.classList.add("hidden");
                message.innerText = "Conversion complete";
                message.style.color = "green";

                if (job.files.length > 1) {
                    downloadAllBtn.disabled = false;
                    downloadAllBtn.classList.remove("hidden");
                }
            }

            if (job.status === "cancelled") {
                clearInterval(poller);
                spinner.classList.add("hidden");
                cancelBtn.classList.add("hidden");
                convertBtn.disabled = false;
                message.innerText = "Job cancelled";
                message.style.color = "orange";
            }
        } catch (e) {
            console.error(e);
        }
    }, 1500);
}

// ================= CANCEL JOB =================
cancelBtn.onclick = () => {
    if (!jobId) return;
    fetch(`/api/cancel/${jobId}`, { method: "POST" });
    message.innerText = "Cancelling job...";
    message.style.color = "orange";
};

// ================= DOWNLOAD ALL ZIP (FIXED) =================
downloadAllBtn.onclick = async () => {
    if (!jobId) return;

    try {
        const res = await fetch("/api/download-zip", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ job_id: jobId })
        });

        if (!res.ok) throw new Error("ZIP download failed");

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "converted_files.zip";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        alert("Download All ZIP failed");
        console.error(e);
    }
};

// ================= RESET =================
// resetBtn.onclick = () => {
//     files = [];
//     jobId = null;
//     clearInterval(poller);
//     fileList.innerHTML = "";
//     spinner.classList.add("hidden");
//     message.innerText = "";
//     convertBtn.disabled = true;
//     cancelBtn.classList.add("hidden");
//     downloadAllBtn.classList.add("hidden");
//     resetBtn.classList.add("hidden");
//     fileInput.value = "";
// };

resetBtn.addEventListener("click", async () => {
    try {
        await fetch("/api/reset-all", { method: "POST" });
    } catch (e) {
        console.warn("Backend reset failed, UI reset only", e);
    }

    // UI reset (existing logic)
    files = [];
    jobId = null;
    if (poller) clearInterval(poller);

    fileList.innerHTML = "";
    spinner.classList.add("hidden");
    message.innerText = "";

    convertBtn.disabled = true;
    cancelBtn.classList.add("hidden");
    downloadAllBtn.classList.add("hidden");
    resetBtn.classList.add("hidden");

    fileInput.value = "";
});

