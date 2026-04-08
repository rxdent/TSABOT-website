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