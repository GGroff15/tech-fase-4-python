(function () {
    'use strict';

    const STREAM_CONSTRAINTS = { audio: true, video: true };

    const statusEl = document.getElementById('status');
    const localVideoEl = document.getElementById('localVideo');
    const remoteAudioEl = document.getElementById('remoteAudio');
    const btnToggleVideo = document.getElementById('btnToggleVideo');
    const btnToggleAudio = document.getElementById('btnToggleAudio');
    const btnToggleAll = document.getElementById('btnToggleAll');

    const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    });

    const detectionChannel = pc.createDataChannel('detections');

    detectionChannel.addEventListener('open', () => {
        console.log('Detection channel opened');
        if (statusEl) statusEl.textContent = 'Connected - streaming video';
    });

    detectionChannel.addEventListener('message', (event) => {
        console.log('Detection data received:', event.data);
    });

    pc.addEventListener('track', (event) => {
        console.log('Remote track received:', event.track && event.track.kind);
        if (event.track && event.track.kind === 'audio' && remoteAudioEl) {
            remoteAudioEl.srcObject = (event.streams && event.streams[0]) || new MediaStream([event.track]);
        }
    });

    let localStream = null;
    let audioSender = null;
    let videoSender = null;
    let isStreamingAudio = false;
    let isStreamingVideo = false;

    function updateButtons() {
        if (!btnToggleVideo || !btnToggleAudio || !btnToggleAll) return;
        btnToggleVideo.textContent = isStreamingVideo ? 'Stop Video' : 'Start Video';
        btnToggleAudio.textContent = isStreamingAudio ? 'Stop Audio' : 'Start Audio';
        btnToggleAll.textContent = (isStreamingAudio || isStreamingVideo) ? 'Stop All' : 'Start All';
    }

    function stopAndRemoveTracks(kind) {
        if (!localStream) return;
        const tracks = kind === 'video' ? localStream.getVideoTracks() : localStream.getAudioTracks();
        tracks.forEach((t) => {
            localStream.removeTrack(t);
            try { t.stop(); } catch (e) { /* ignore */ }
        });
    }

    async function toggleVideo() {
        if (!btnToggleVideo) return;
        btnToggleVideo.disabled = true;
        try {
            if (isStreamingVideo) {
                stopAndRemoveTracks('video');
                if (videoSender?.replaceTrack) await videoSender.replaceTrack(null);
                // replace last frame with a black image
                if (localVideoEl) {
                    const w = localVideoEl.videoWidth || localVideoEl.clientWidth || 640;
                    const h = localVideoEl.videoHeight || localVideoEl.clientHeight || 480;
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = w;
                        canvas.height = h;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = 'black';
                        ctx.fillRect(0, 0, w, h);
                        const dataUrl = canvas.toDataURL('image/png');
                        try { localVideoEl.srcObject = null; } catch (e) {}
                        localVideoEl.pause();
                        localVideoEl.poster = dataUrl;
                        try { localVideoEl.load(); } catch (e) {}
                    } catch (e) {
                        // fallback: set black background
                        localVideoEl.style.background = 'black';
                    }
                }
                isStreamingVideo = false;
            } else {
                const s = await navigator.mediaDevices.getUserMedia({ video: true });
                const newTrack = s.getVideoTracks()[0];
                if (!localStream) localStream = new MediaStream();
                localStream.addTrack(newTrack);
                if (videoSender?.replaceTrack) {
                    await videoSender.replaceTrack(newTrack);
                } else {
                    videoSender = pc.addTrack(newTrack, localStream);
                }
                if (localVideoEl) {
                    // remove any placeholder poster or black background when starting
                    try { localVideoEl.removeAttribute('poster'); } catch (e) {}
                    localVideoEl.style.background = '';
                    localVideoEl.srcObject = localStream;
                }
                isStreamingVideo = true;
            }
        } catch (err) {
            console.error('toggleVideo error', err);
            if (statusEl) statusEl.textContent = 'Error: ' + (err && err.message);
        } finally {
            updateButtons();
            btnToggleVideo.disabled = false;
        }
    }

    async function toggleAudio() {
        if (!btnToggleAudio) return;
        btnToggleAudio.disabled = true;
        try {
            if (isStreamingAudio) {
                stopAndRemoveTracks('audio');
                if (audioSender?.replaceTrack) await audioSender.replaceTrack(null);
                isStreamingAudio = false;
            } else {
                const s = await navigator.mediaDevices.getUserMedia({ audio: true });
                const newTrack = s.getAudioTracks()[0];
                if (!localStream) localStream = new MediaStream();
                localStream.addTrack(newTrack);
                if (audioSender?.replaceTrack) await audioSender.replaceTrack(newTrack);
                else audioSender = pc.addTrack(newTrack, localStream);
                isStreamingAudio = true;
            }
        } catch (err) {
            console.error('toggleAudio error', err);
            if (statusEl) statusEl.textContent = 'Error: ' + (err && err.message);
        } finally {
            updateButtons();
            btnToggleAudio.disabled = false;
        }
    }

    async function toggleAll() {
        if (!btnToggleAll) return;
        btnToggleAll.disabled = true;
        try {
            if (isStreamingAudio || isStreamingVideo) {
                await Promise.all([
                    isStreamingVideo ? toggleVideo() : Promise.resolve(),
                    isStreamingAudio ? toggleAudio() : Promise.resolve()
                ]);
            } else {
                await Promise.all([toggleVideo(), toggleAudio()]);
            }
        } finally {
            btnToggleAll.disabled = false;
        }
    }

    if (btnToggleVideo) btnToggleVideo.addEventListener('click', toggleVideo);
    if (btnToggleAudio) btnToggleAudio.addEventListener('click', toggleAudio);
    if (btnToggleAll) btnToggleAll.addEventListener('click', toggleAll);

    async function startInitialStream() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia(STREAM_CONSTRAINTS);
            console.log('Got media stream');
            if (statusEl) statusEl.textContent = 'Camera accessed, connecting...';
            localStream = stream;
            if (localVideoEl) localVideoEl.srcObject = localStream;

            stream.getTracks().forEach((track) => {
                console.log('Adding track:', track.kind);
                pc.addTrack(track, stream);
            });

            pc.getSenders().forEach((s) => {
                if (s.track && s.track.kind === 'audio') audioSender = s;
                if (s.track && s.track.kind === 'video') videoSender = s;
            });

            isStreamingAudio = !!audioSender;
            isStreamingVideo = !!videoSender;
            updateButtons();

            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);

            const resp = await fetch('/offer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type })
            });
            const answer = await resp.json();
            await pc.setRemoteDescription(new RTCSessionDescription(answer));
            console.log('Connection established');
        } catch (err) {
            console.error('startInitialStream error', err);
            if (statusEl) statusEl.textContent = 'Error: ' + (err && err.message);
        }
    }

    // Start when script is parsed (defer script ensures DOM is ready)
    startInitialStream();
})();
