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

    sectionSelect.innerHTML = '<option value="all">All Sections</option>';

    if (unitId === "all") return;

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

    let topic = "All Topics";

    if (section !== "all") topic = section;
    else if (unit !== "all") topic = unit;

    document.getElementById("chat-container").classList.remove("hidden");

    addMessage("bot", "How may I help you?\n- Explain a topic\n- Give examples\n- Help me study\n- Ask questions");

    window.currentTopic = topic;
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