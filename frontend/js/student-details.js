function addStudentDetail(content, label, value) {
    const term = document.createElement("dt");
    term.className = "student-detail-label";
    term.textContent = label;

    const description = document.createElement("dd");
    description.className = "student-detail-value";
    description.textContent = value == null || value === "" ? "Not available" : String(value);
    content.append(term, description);
}

async function loadStudentDetails() {
    const status = document.getElementById("studentDetailsStatus");
    const content = document.getElementById("studentDetailsContent");
    const usn = new URLSearchParams(window.location.search).get("usn");

    if (!usn || !usn.trim()) {
        status.textContent = "No student USN was provided. Return to the student list and select a student.";
        return;
    }

    try {
        const response = await fetch(`${API}/${encodeURIComponent(usn)}`);
        if (!response.ok) {
            let message = `Student service returned HTTP ${response.status}.`;
            try {
                const error = await response.json();
                if (error.detail) message = error.detail;
            } catch {
                // Keep the HTTP status message when the response has no JSON error body.
            }
            throw new Error(message);
        }

        const student = await response.json();
        if (!student || typeof student !== "object" || Array.isArray(student)) {
            throw new Error("Student details could not be loaded. Please return to the list and try again.");
        }

        const fields = [
            ["Name", student.name],
            ["USN", student.usn],
            ["Branch", student.branch],
            ["Year", student.year],
            ["Email", student.email],
            ["Backlogs", student.backlog_count],
        ];
        if (student.attendance_pct != null) fields.push(["Attendance", `${student.attendance_pct}%`]);
        if (student.previous_gpa != null) fields.push(["CGPA", student.previous_gpa]);
        fields.forEach(([label, value]) => addStudentDetail(content, label, value));
        status.textContent = "";
    } catch (error) {
        status.textContent = `Unable to load student details: ${error.message}`;
        status.setAttribute("role", "alert");
    }
}

window.addEventListener("DOMContentLoaded", loadStudentDetails);
