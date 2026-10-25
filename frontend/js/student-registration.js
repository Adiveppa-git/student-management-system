// PART 1: Existing Student CRUD Logic (Preserved 100%)
// =========================================================================
let editUSN = null;
let successMessageTimeout;

function clearSuccessMessage() {
    const successMessage = document.getElementById("studentSuccessMessage");
    successMessage.textContent = "";
    successMessage.hidden = true;
    window.clearTimeout(successMessageTimeout);
}

function showSuccessMessage(message) {
    const successMessage = document.getElementById("studentSuccessMessage");
    successMessage.textContent = message;
    successMessage.hidden = false;

    successMessageTimeout = window.setTimeout(() => {
        successMessage.hidden = true;
    }, 4500);
}

// Add / Update
document.getElementById("studentForm").onsubmit = async (e) => {
    e.preventDefault();
    clearSuccessMessage();

    const nameInput = document.getElementById("name");
    const usnInput = document.getElementById("usn");
    const branchInput = document.getElementById("branch");
    const yearInput = document.getElementById("year");
    const emailInput = document.getElementById("email");
    const submitBtn = document.getElementById("submitBtn");

    const student = {
        name: nameInput.value.trim(),
        usn: usnInput.value.trim().toUpperCase(),
        branch: branchInput.value.trim(),
        year: parseInt(yearInput.value),
        email: emailInput.value.trim()
    };

    try {
        if (editUSN) {
            const res = await fetch(`${API}/${encodeURIComponent(editUSN)}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(student)
            });

            if (!res.ok) {
                const err = await res.json();
                alert("Error updating student: " + (err.detail || "Update failed"));
                return;
            }

            showSuccessMessage("Student updated successfully! ✅");
            return;
        } else {
            const res = await fetch(API, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(student)
            });

            if (!res.ok) {
                const err = await res.json();
                alert("Error adding student: " + (err.detail || "Creation failed"));
                return;
            }

            showSuccessMessage("Student registered successfully! ✅");
        }

        document.getElementById("studentForm").reset();
    } catch (networkErr) {
        alert("Network error communicating with backend API: " + networkErr.message);
    }
};

async function loadStudentForEdit() {
    const usn = new URLSearchParams(window.location.search).get("usn");
    if (!usn) return;

    try {
        const response = await fetch(`${API}/${encodeURIComponent(usn)}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Unable to load student.");
        }

        const student = await response.json();
        document.getElementById("name").value = student.name || "";
        document.getElementById("usn").value = student.usn || "";
        document.getElementById("branch").value = student.branch || "";
        document.getElementById("year").value = student.year || "";
        document.getElementById("email").value = student.email || "";
        editUSN = student.usn;

        const submitButton = document.getElementById("submitBtn");
        submitButton.textContent = "Update Student";
        submitButton.className = "updateBtn";
        document.getElementById("name").focus();
    } catch (error) {
        alert(`Error loading student: ${error.message}`);
    }
}

window.addEventListener("DOMContentLoaded", loadStudentForEdit);
