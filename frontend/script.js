document.addEventListener('DOMContentLoaded', () => {
    const recordBtn = document.getElementById('recordBtn');
    const micIcon = document.getElementById('micIcon');
    const playBtn = document.getElementById('playBtn');
    const status = document.getElementById('status');

    // Backend URL - change this if you're using a different URL
    const backendUrl = 'https://talking-agent-backend.onrender.com';

    if (!recordBtn || !micIcon || !playBtn || !status) {
        console.error('Elements not found: recordBtn, micIcon, playBtn, or status');
        return;
    }

    // First check if backend is reachable
    status.textContent = 'Checking connection to server...';
    
    // Try a simple request to check server connection
    fetch(`${backendUrl}/test`, { method: 'GET', mode: 'no-cors' })
        .then(() => {
            status.textContent = 'Server connection established. Ready to record.';
            console.log('Backend connection established');
        })
        .catch(error => {
            console.warn('Backend connection test failed:', error);
            status.textContent = 'Warning: Server connection issue. Recording may not work.';
        });

    let audioBlob = null; // Store the response audio for playback

    recordBtn.addEventListener('click', async () => {
        console.log('Speak Now button clicked');
        try {
            // Reset UI
            status.textContent = 'Requesting microphone access...';
            playBtn.classList.add('hidden');
            audioBlob = null;

            // Request microphone access
            console.log('Requesting microphone access...');
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log('Microphone access granted');

            // Create media recorder
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm'
            });
            const chunks = [];

            // Update UI to show recording state
            mediaRecorder.start();
            console.log('Recording started');
            recordBtn.textContent = 'Recording...';
            recordBtn.classList.remove('bg-red-500', 'hover:bg-red-600');
            recordBtn.classList.add('bg-red-700', 'animate-pulse');
            micIcon.classList.add('animate-pulse', 'text-yellow-300');
            status.textContent = 'Listening...';

            mediaRecorder.ondataavailable = (e) => {
                chunks.push(e.data);
                console.log('Audio chunk recorded:', e.data);
            };

            mediaRecorder.onstop = async () => {
                console.log('Recording stopped');
                recordBtn.textContent = 'Speak Now';
                recordBtn.classList.remove('bg-red-700', 'animate-pulse');
                recordBtn.classList.add('bg-red-500', 'hover:bg-red-600');
                micIcon.classList.remove('animate-pulse', 'text-yellow-300');
                status.textContent = 'Processing...';

                // Create blob from recorded chunks
                const blob = new Blob(chunks, { type: 'audio/webm' });
                console.log('Audio blob created:', blob);

                // Prepare FormData for server
                const formData = new FormData();
                formData.append('audio', blob, 'recording.webm');
                console.log('Sending audio to back-end...');

                // Try multiple approaches to connect to backend
                try {
                    let response;
                    
                    // First attempt: Regular CORS request
                    try {
                        response = await fetch(`${backendUrl}/conversation`, {
                            method: 'POST',
                            body: formData,
                            mode: 'cors'
                        });
                    } catch (corsError) {
                        console.warn('CORS request failed, trying no-cors mode:', corsError);
                        
                        // Second attempt: no-cors mode (limited but might work for some cases)
                        response = await fetch(`${backendUrl}/conversation`, {
                            method: 'POST',
                            body: formData,
                            mode: 'no-cors'
                        });
                        
                        // Note: with no-cors, we can't check response.ok or get the response content
                        // This is a limitation of the no-cors mode
                        status.textContent = 'Request sent in no-cors mode. Check server logs.';
                        return;
                    }

                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error(`Server responded with ${response.status}: ${errorText}`);
                        throw new Error(`Server error: ${response.status} - ${errorText}`);
                    }

                    console.log('Response received from back-end');
                    audioBlob = await response.blob();
                    
                    // Show the play button and update status
                    playBtn.classList.remove('hidden');
                    status.textContent = 'Response ready! Click "Play Response" to listen.';
                } catch (fetchError) {
                    console.error('Fetch error:', fetchError);
                    status.textContent = 'Error connecting to server: ' + fetchError.message;
                    
                    // Display more helpful message
                    const additionalInfo = document.createElement('div');
                    additionalInfo.innerHTML = `
                        <div class="mt-4 text-sm text-red-500">
                            <p>Server connection failed. Possible issues:</p>
                            <ul class="list-disc ml-5 mt-2">
                                <li>Backend server might be down</li>
                                <li>CORS configuration issue on the server</li>
                                <li>Network connectivity problem</li>
                            </ul>
                        </div>
                    `;
                    status.appendChild(additionalInfo);
                }
            };

            // Stop recording after 5 seconds
            setTimeout(() => {
                if (mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                    console.log('Recording stopped after timeout');
                }
            }, 5000);
        } catch (error) {
            console.error('Error:', error);
            recordBtn.textContent = 'Speak Now';
            recordBtn.classList.remove('bg-red-700', 'animate-pulse');
            micIcon.classList.remove('animate-pulse', 'text-yellow-300');
            recordBtn.classList.add('bg-red-500', 'hover:bg-red-600');
            status.textContent = 'Error: ' + error.message;
        }
    });

    playBtn.addEventListener('click', () => {
        if (audioBlob) {
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();
            status.textContent = 'Playing response...';
            console.log('Playing response audio');
            
            audio.onended = () => {
                status.textContent = 'Playback complete. Click "Speak Now" to record again.';
            };
            
            audio.onerror = (e) => {
                console.error('Audio playback error:', e);
                status.textContent = 'Error playing audio.';
            };
        } else {
            status.textContent = 'No response audio available.';
        }
    });
});