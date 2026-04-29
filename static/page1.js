function goToTest() {
    window.location.href = "/test_mode";
}

function startFullTest() {
    window.location.href = "/test/answer";
}

function goToHome() {
    window.location.href = "/";
}

function goToPractice() {
    window.location.href = "/practice";
}

function goToStudyGuide() {
    window.location.href = "/study/guide";
}

function goToWeakTopics() {
    window.location.href = "/study/weak";
}

function goToStudyHome() {
    window.location.href = "/study";
}


function handleTestNavigation(event) {
    const button = event.submitter;
    
    // Only show loading if clicking "Next"
    if (button && button.value === "next") {
        const container = document.querySelector('.test-container');
        const currentIndex = parseInt(container.getAttribute('data-index'));
        const totalFetched = parseInt(container.getAttribute('data-fetched'));

        // If index + 1 >= totalFetched, the app.py logic will trigger generate_question()
        if (currentIndex + 1 >= totalFetched) {
            document.getElementById('loading-overlay').style.display = 'flex';
        }
    }
}

function triggerLoading(message, url) {
    document.getElementById('loading-message').innerText = message;
    document.getElementById('loading-overlay').style.display = 'flex';
    window.location.href = url;
}

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const main = document.getElementById("mainContainer");
    const btn = document.querySelector(".toggle-btn");

    // Toggle the classes
    sidebar.classList.toggle("collapsed");
    main.classList.toggle("full");
    
    // If you are using the 'pushed' class for the button:
    if (btn) {
        btn.classList.toggle("pushed");
    }
}


// STUDY MODE ------------

// Populate sections dynamically
function populateSections() {
    const unitId = document.getElementById("unit-select").value;
    const sectionSelect = document.getElementById("section-select");

    sectionSelect.innerHTML =
        '<option value="all">Whole unit</option>';

    if (unitId === "all") {
        unitsData.units.forEach(unit => {
            unit.sections.forEach(sec => {
                const opt = document.createElement("option");
                opt.value = sec.id;
                opt.textContent =
                    `Unit ${unit.unit} - ${sec.section}`;
                sectionSelect.appendChild(opt);
            });
        });
        return;
    }

    const unit = unitsData.units.find(u => u.id === unitId);

    if (!unit) return;

    unit.sections.forEach(sec => {
        const opt = document.createElement("option");
        opt.value = sec.id;
        opt.textContent = sec.section;
        sectionSelect.appendChild(opt);
    });
}

// Start study → show chatbot
function startStudy() {
    const unit = document.getElementById("unit-select").value;
    const section = document.getElementById("section-select").value;

    let topic = "all";

    if (section !== "all") {
        topic = section;
    } else if (unit !== "all") {
        topic = unit;
    }

    const chatContainer = document.getElementById("chat-container");
    const chatBox = document.getElementById("chat-box");

    chatBox.innerHTML = "";

    chatContainer.classList.remove("hidden");

    window.currentTopic = topic;

    addMessage("bot",
        "How may I help you?\n- Explain a weak topic\n- Give examples\n- Quiz me\n- Help me improve"
    );
}


// CHAT SYSTEM
function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();

    if (!text) return;

    addMessage("user", text);
    input.value = "";

    fetch("/study/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            message: text,
            topic: window.currentTopic
        })
    })
    .then(res => res.json())
    .then(data => {
        addMessage("bot", data.response);
    });
}


function addMessage(sender, text) {
    const box = document.getElementById("chat-box");

    const div = document.createElement("div");
    div.className = sender === "user" ? "msg user-msg" : "msg bot-msg";
    div.innerText = text;

    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("chat-input");

    if (input) {
        input.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault(); // prevent newline
                sendMessage();
            }
        });
    }
});

// PRACTICE AI CHATBOT

function showCorrectFeedback() {
    const oldBox = document.getElementById("practice-feedback");

    if (oldBox) oldBox.remove();

    const box = document.createElement("div");
    box.id = "practice-feedback";
    box.className = "feedback-box";
    box.innerHTML = `<p style="color:#4ade80;">Correct!</p>`;

    document.querySelector(".nav-buttons")
        .before(box);
}

let practiceHistory = [];
let waitingForReply = false;

function submitPracticeAnswer() {
    const selected = document.querySelector('input[name="answer"]:checked');

    if (!selected) {
        alert("Select an answer first.");
        return;
    }

    const chosen = selected.value;

    const container = document.getElementById("mainContainer");
    const correct = container.dataset.correct;

    const formData = new FormData();
    formData.append("answer", chosen);

    fetch("/test/answer", {
        method: "POST",
        headers: {
            "X-Requested-With": "XMLHttpRequest"
        },
        body: formData
    })
    .then(res => res.json())
    .then(data => {

        if (chosen === correct) {
            showCorrectFeedback();
        } else {
            openPracticeChat(chosen);
        }

    })
    .catch(err => console.error(err));
}


function openPracticeChat(selectedLetter) {
    document
        .getElementById("practice-chat-modal")
        .classList.remove("hidden");

    document.getElementById("practice-chat-box").innerHTML = "";

    practiceHistory = [];

    requestPracticeReply(selectedLetter, []);
}

function requestPracticeReply(selectedLetter, history) {
    const container = document.getElementById("mainContainer");

    showThinking();

    fetch("/practice/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            topic: container.dataset.topic,
            question: container.dataset.question,
            options: JSON.parse(container.dataset.options),
            selected: selectedLetter,
            correct: container.dataset.correct,
            history: history
        })
    })
    .then(res => res.json())
    .then(data => {
        removeThinking();
        typeBotMessage(data.response);

        practiceHistory.push({
            role: "assistant",
            content: data.response
        });
    });
}

function sendPracticeMessage() {
    if (waitingForReply) return;

    const input = document.getElementById("practice-chat-input");
    const text = input.value.trim();

    if (!text) return;

    addPracticeMessage("user", text);

    practiceHistory.push({
        role: "user",
        content: text
    });

    input.value = "";

    const selected = document.querySelector('input[name="answer"]:checked').value;

    requestPracticeReply(selected, practiceHistory);
}

function addPracticeMessage(sender, text) {
    const box = document.getElementById("practice-chat-box");

    const div = document.createElement("div");
    div.className = sender === "user" ? "msg user-msg" : "msg bot-msg";
    div.innerText = text;

    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

function typeBotMessage(text) {
    waitingForReply = true;

    const box = document.getElementById("practice-chat-box");
    const div = document.createElement("div");

    div.className = "msg bot-msg";
    box.appendChild(div);

    let i = 0;

    const interval = setInterval(() => {
        div.innerText = text.slice(0, i);
        box.scrollTop = box.scrollHeight;
        i++;

        if (i > text.length) {
            clearInterval(interval);
            waitingForReply = false;
        }
    }, 14);
}

function showThinking() {
    const box = document.getElementById("practice-chat-box");

    const div = document.createElement("div");
    div.className = "msg bot-msg thinking-msg";
    div.id = "thinking-msg";
    div.innerText = "Thinking...";

    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

function removeThinking() {
    const thinking = document.getElementById("thinking-msg");
    if (thinking) thinking.remove();
}

function closePracticeChat() {
    document.getElementById("practice-chat-modal").classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("practice-chat-input");

    if (input) {
        input.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                e.preventDefault();
                sendPracticeMessage();
            }
        });
    }
});