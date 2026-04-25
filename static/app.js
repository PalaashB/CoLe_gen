document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const generateBtn = document.getElementById('generateBtn');
    const jobInput = document.getElementById('jobInput');
    const toneSelect = document.getElementById('toneSelect');
    
    const statusContainer = document.getElementById('statusContainer');
    const statusList = document.getElementById('statusList');
    const researchLoader = document.getElementById('researchLoader');
    
    const letterContainer = document.getElementById('letterContainer');
    const letterContent = document.getElementById('letterContent');
    const scoreBadge = document.getElementById('scoreBadge');
    const scoreValue = document.getElementById('scoreValue');
    const downloadActions = document.getElementById('downloadActions');
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    const historyList = document.getElementById('historyList');

    let currentPdfPath = null;

    // Load History
    fetchHistory();

    generateBtn.addEventListener('click', async () => {
        const text = jobInput.value.trim();
        if (!text) {
            alert("Please paste a job description or URL first.");
            return;
        }

        // Reset UI
        statusList.innerHTML = '';
        statusContainer.classList.remove('hidden');
        letterContainer.classList.add('hidden');
        downloadActions.classList.add('hidden');
        letterContent.innerHTML = '';
        generateBtn.disabled = true;
        generateBtn.textContent = 'Working...';
        jobInput.parentElement.classList.add('disabled-area');
        researchLoader.style.display = 'block';

        try {
            // Because SSE EventSource only supports GET natively, we use fetch to read the stream
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_text: text, tone: toneSelect.value })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                
                buffer = lines.pop(); // Keep the incomplete line in the buffer

                for (let block of lines) {
                    if (block.trim() === '') continue;
                    
                    let eventType = "message";
                    let data = "";
                    
                    block.split('\n').forEach(line => {
                        if (line.startsWith('event: ')) eventType = line.substring(7);
                        if (line.startsWith('data: ')) data = line.substring(6);
                    });

                    if (data) {
                        try {
                            handleStreamEvent(eventType, JSON.parse(data));
                        } catch (e) {
                            console.error("Error parsing JSON data:", data);
                        }
                    }
                }
            }

        } catch (error) {
            console.error("Generation failed:", error);
            addStatusItem("Generation failed. Check console.", true);
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Letter';
            jobInput.parentElement.classList.remove('disabled-area');
            researchLoader.style.display = 'none';
        }
    });

    function handleStreamEvent(event, data) {
        if (event === "parsing") {
            addStatusItem(data.message);
        } else if (event === "parsed") {
            addStatusItem(`Detected: ${data.job_data.company_name} - ${data.job_data.position_title}`, true);
        } else if (event === "research_progress") {
            addStatusItem(`[${data.step}] ${data.message}`);
        } else if (event === "content") {
            // First chunk of content means research is done, show letter container
            if (letterContainer.classList.contains('hidden')) {
                letterContainer.classList.remove('hidden');
                scoreBadge.style.opacity = '0'; // Hide score until done
            }
            // Append chunk
            letterContent.innerHTML += data.text;
            // Auto scroll container
            letterContent.scrollTop = letterContent.scrollHeight;
        } else if (event === "done") {
            // Finalize UI
            scoreValue.textContent = data.quality_score;
            scoreBadge.style.opacity = '1';
            
            scoreBadge.className = 'score-badge'; // reset
            if (data.quality_score < 60) scoreBadge.classList.add('low');
            else if (data.quality_score < 80) scoreBadge.classList.add('average');
            
            if (data.pdf_path) {
                currentPdfPath = data.pdf_path;
                downloadActions.classList.remove('hidden');
            }
            
            addStatusItem("Complete!", true);
            fetchHistory(); // refresh sidebar
        } else if (event === "error") {
            addStatusItem(`Error: ${data.message}`, true);
            alert(data.message);
        }
    }

    function addStatusItem(message, isDone = false) {
        const li = document.createElement('li');
        li.className = 'status-item';
        if (isDone) li.classList.add('done');
        
        li.innerHTML = `
            <span style="margin-right:8px;">${isDone ? '✓' : '⟳'}</span>
            <span>${message}</span>
        `;
        
        // replace previous item if it's just an update, unless it's marked done.
        // For simplicity, just append.
        statusList.appendChild(li);
        
        // Auto trim status list to stop it getting too huge visually
        if(statusList.children.length > 8) {
            statusList.removeChild(statusList.firstChild);
        }
    }

    async function fetchHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            
            historyList.innerHTML = '';
            
            if (data.history.length === 0) {
                historyList.innerHTML = '<p style="color:var(--text-secondary); text-align:center; margin-top:2rem;">No applications yet</p>';
                return;
            }
            
            // Reverse so newest is first
            [...data.history].reverse().forEach(item => {
                const el = document.createElement('div');
                el.className = 'history-item';
                
                const dateRaw = new Date(item.date);
                const dateStr = dateRaw.toLocaleDateString() + ' ' + dateRaw.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                
                el.innerHTML = `
                    <h4>${item.company}</h4>
                    <p style="margin-bottom:0.25rem; font-weight:500;">${item.position}</p>
                    <p style="font-size:0.75rem; display:flex; justify-content:space-between;">
                        <span>Score: ${item.quality_score}</span>
                        <span>${dateStr}</span>
                    </p>
                `;
                
                el.addEventListener('click', () => {
                    letterContainer.classList.remove('hidden');
                    letterContent.innerHTML = item.letter_preview + '\n\n... (preview)';
                    scoreValue.textContent = item.quality_score;
                    scoreBadge.className = 'score-badge';
                    if (item.quality_score < 60) scoreBadge.classList.add('low');
                    else if (item.quality_score < 80) scoreBadge.classList.add('average');
                    scoreBadge.style.opacity = '1';
                    
                    if (item.pdf_path) {
                        currentPdfPath = item.pdf_path;
                        downloadActions.classList.remove('hidden');
                    } else {
                        downloadActions.classList.add('hidden');
                    }
                });
                
                historyList.appendChild(el);
            });
        } catch(e) {
            console.error("Could not fetch history", e);
        }
    }

    downloadPdfBtn.addEventListener('click', () => {
        if (!currentPdfPath) return;
        // In a real production app we'd have a download endpoint. 
        // For this local tool, we might just alert the path, or if we serve the data dir:
        alert(`Your PDF is saved at:\n${currentPdfPath}`);
    });
});
