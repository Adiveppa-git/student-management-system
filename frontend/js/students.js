let showAllStudents = false;

function createStudentAction(label, className, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", action);
    return button;
}

function viewStudent(student) {
    window.location.href = `student-details.html?usn=${encodeURIComponent(student.usn)}`;
}

async function deleteStudent(usn) {
    if (!window.confirm(`Are you sure you want to delete student with USN: ${usn}?`)) return;

    try {
        const response = await fetch(`${API}/${encodeURIComponent(usn)}`, { method: "DELETE" });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Deletion failed");
        }
        window.alert("Student deleted.");
        await loadStudents();
    } catch (error) {
        window.alert(`Error deleting student: ${error.message}`);
    }
}

async function loadStudents() {
    const studentList = document.getElementById("studentList");
    studentList.replaceChildren();

    try {
        const response = await fetch(API);
        if (!response.ok) throw new Error(`Student service returned HTTP ${response.status}.`);
        const students = await response.json();

        if (students.length === 0) {
            const emptyMessage = document.createElement("li");
            emptyMessage.textContent = "No students have been registered yet.";
            studentList.appendChild(emptyMessage);
            return;
        }

        const visibleStudents = showAllStudents ? students : students.slice(0, 3);
        visibleStudents.forEach((student, index) => {
            const item = document.createElement("li");
            const summary = document.createElement("span");
            summary.textContent = `${index + 1}. ${student.name} (${student.usn}) - ${student.branch || ""} Year ${student.year || ""}`;

            const actions = document.createElement("div");
            actions.append(
                createStudentAction("View", "viewBtn", () => viewStudent(student)),
                createStudentAction("Edit", "editBtn", () => {
                    window.location.href = `index.html?usn=${encodeURIComponent(student.usn)}`;
                }),
                createStudentAction("Delete", "deleteBtn", () => deleteStudent(student.usn)),
            );
            item.append(summary, actions);
            studentList.appendChild(item);
        });

        if (students.length > 3) {
            const pagination = document.createElement("li");
            pagination.className = "student-list-toggle";
            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "viewBtn";
            toggle.textContent = showAllStudents ? "Show Less" : "View More";
            toggle.addEventListener("click", () => {
                showAllStudents = !showAllStudents;
                loadStudents();
            });
            pagination.appendChild(toggle);
            studentList.appendChild(pagination);
        }
    } catch (error) {
        const message = document.createElement("li");
        message.className = "student-list-error";
        message.textContent = `Unable to load students: ${error.message}`;
        studentList.replaceChildren(message);
    }
}

window.addEventListener("DOMContentLoaded", loadStudents);


// =========================================================================
