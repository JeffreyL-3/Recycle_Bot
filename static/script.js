var capturedImageFile = null;
var cameraStream = null;
var loadingInterval = null;
var isSubmitting = false;
var currentFlow = 'choice';
var flowVersion = 0;
var topBarStatusTimer = null;

function toggleNav(special = 0) {
    var sidebar = document.getElementById("mySidebar");

    if (special == 1) {
        sidebar.style.bottom = "-320px";
    } else if (special == 2) {
        sidebar.style.bottom = "0px";
    } else if (sidebar.style.bottom === "0px") {
        sidebar.style.bottom = "-320px";
    } else {
        sidebar.style.bottom = "0px";
    }
}

// On small screens the flyout menu is pinned to the bottom of the viewport and
// can cover the centered UI. This runs ONCE on load (while the flyout is open)
// to lift the whole UI up just enough to clear the flyout -- but never so far
// that it slides under the top bar (hamburger / model / Use Location). The resulting
// position is then locked in: it does not react to flyout toggles or resizing.
function lockLayoutForFlyout() {
    var container = document.querySelector('.container');
    var sidebar = document.getElementById('mySidebar');
    var heading = container ? container.querySelector('h1') : null;

    if (!container || window.innerWidth > 600) {
        return;
    }

    var gap = 16;                 // breathing room between UI and flyout
    var topBar = document.querySelector('.top-bar');
    var topBarBottom = topBar ? topBar.getBoundingClientRect().bottom + 12 : 72;
    var flyoutTop = window.innerHeight - sidebar.offsetHeight;
    var containerRect = container.getBoundingClientRect();

    var overlap = containerRect.bottom + gap - flyoutTop;
    if (overlap <= 0) {
        return; // already fits above the flyout; no lift needed
    }

    // Don't lift past the top bar: the topmost visible element must stay below it.
    var contentTop = heading ? heading.getBoundingClientRect().top : containerRect.top;
    var maxShift = Math.max(0, contentTop - topBarBottom);
    var shift = Math.min(overlap, maxShift);

    if (shift > 0) {
        container.style.transform = 'translateY(-' + shift + 'px)';
    }
}

function getFlowElements() {
    return {
        choiceScreen: document.getElementById('choice-screen'),
        actionScreen: document.getElementById('action-screen'),
        instruction: document.getElementById('flow-instruction'),
        status: document.getElementById('flow-status'),
        backButton: document.getElementById('backButton'),
        captureButton: document.getElementById('capturePhotoButton'),
        uploadInput: document.getElementById('image'),
        cameraInput: document.getElementById('camera-image'),
        video: document.getElementById('camera-preview')
    };
}

function clearFileInputs() {
    var elements = getFlowElements();
    elements.uploadInput.value = '';
    elements.cameraInput.value = '';
}

function showChoiceScreen() {
    var elements = getFlowElements();
    currentFlow = 'choice';
    flowVersion++;
    elements.choiceScreen.hidden = false;
    elements.actionScreen.hidden = true;
    elements.captureButton.hidden = true;
    elements.backButton.disabled = false;
    elements.instruction.textContent = '';
    elements.status.textContent = '';
}

function showActionScreen(instructionText, statusText) {
    var elements = getFlowElements();
    elements.choiceScreen.hidden = true;
    elements.actionScreen.hidden = false;
    elements.instruction.textContent = instructionText;
    elements.status.textContent = statusText || '';
    elements.backButton.disabled = false;
}

function resetImageFlow() {
    if (isSubmitting) {
        return;
    }

    stopCamera();
    currentFlow = 'choice';
    flowVersion++;
    clearFileInputs();
    capturedImageFile = null;
    document.getElementById('result').innerHTML = '';
    showChoiceScreen();
    toggleNav(2); // back on the home screen: re-show the flyout
}

function startUploadFlow() {
    if (isSubmitting) {
        return;
    }

    stopCamera();
    currentFlow = 'upload';
    flowVersion++;
    clearFileInputs();
    capturedImageFile = null;
    document.getElementById('result').innerHTML = '';
    showActionScreen('Upload your photo', 'Choose an image from your device.');
    toggleNav(1); // leaving the home screen: hide the flyout
    getFlowElements().uploadInput.click();
}

function startPhotoFlow() {
    if (isSubmitting) {
        return;
    }

    clearFileInputs();
    currentFlow = 'photo';
    flowVersion++;
    var photoFlowVersion = flowVersion;
    capturedImageFile = null;
    document.getElementById('result').innerHTML = '';
    showActionScreen('Take your photo...', 'Opening camera.');
    toggleNav(1); // leaving the home screen: hide the flyout

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        getFlowElements().cameraInput.click();
        return;
    }

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
        .then(function(stream) {
            var elements = getFlowElements();

            if (currentFlow !== 'photo' || flowVersion !== photoFlowVersion) {
                stream.getTracks().forEach(function(track) {
                    track.stop();
                });
                return;
            }

            cameraStream = stream;
            elements.video.srcObject = stream;
            elements.video.hidden = false;
            elements.captureButton.hidden = false;
            elements.captureButton.disabled = false;
            elements.status.textContent = 'Point the camera at the item, then capture.';
            fitCameraToViewport();
        })
        .catch(function() {
            if (currentFlow !== 'photo' || flowVersion !== photoFlowVersion) {
                return;
            }

            var elements = getFlowElements();
            elements.status.textContent = 'Choose or take a photo from your device.';
            elements.cameraInput.click();
        });
}

// Size the live camera preview so the Capture Photo button always sits
// directly below the feed AND stays within the viewport. Without this the
// preview grows to its CSS max-height and pushes the button off-screen on
// shorter devices, forcing the user to scroll to capture.
function fitCameraToViewport() {
    var elements = getFlowElements();
    var video = elements.video;

    if (video.hidden) {
        return;
    }

    var videoTop = video.getBoundingClientRect().top;
    // Room to keep below the feed for the capture button + a little breathing space.
    var reserve = (elements.captureButton.offsetHeight || 56) + 48;
    var available = window.innerHeight - videoTop - reserve;

    video.style.maxHeight = Math.max(180, available) + 'px';
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(function(track) {
            track.stop();
        });
        cameraStream = null;
    }

    var elements = getFlowElements();
    elements.video.hidden = true;
    elements.video.srcObject = null;
    elements.video.style.maxHeight = '';
    elements.captureButton.hidden = true;
    elements.captureButton.disabled = false;
}

function dataUrlToBlob(dataUrl) {
    var parts = dataUrl.split(',');
    var mime = parts[0].match(/:(.*?);/)[1];
    var binary = atob(parts[1]);
    var array = new Uint8Array(binary.length);

    for (var i = 0; i < binary.length; i++) {
        array[i] = binary.charCodeAt(i);
    }

    return new Blob([array], { type: mime });
}

function submitCanvas(canvas) {
    var fileName = 'camera-photo.jpg';
    var photoFlowVersion = flowVersion;
    var saveBlob = function(blob) {
        if (currentFlow !== 'photo' || flowVersion !== photoFlowVersion) {
            return;
        }

        if (!blob) {
            getFlowElements().status.textContent = 'Could not capture photo. Please try again.';
            getFlowElements().captureButton.disabled = false;
            return;
        }

        capturedImageFile = blob;
        stopCamera();
        sendFormData(blob, fileName);
    };

    if (canvas.toBlob) {
        canvas.toBlob(saveBlob, 'image/jpeg', 0.9);
    } else {
        saveBlob(dataUrlToBlob(canvas.toDataURL('image/jpeg', 0.9)));
    }
}

function capturePhoto() {
    var video = document.getElementById('camera-preview');
    var canvas = document.getElementById('camera-canvas');
    var elements = getFlowElements();

    if (!cameraStream) {
        startPhotoFlow();
        return;
    }

    if (!video.videoWidth || !video.videoHeight) {
        elements.status.textContent = 'Camera is starting. Try again in a moment.';
        return;
    }

    if (elements.captureButton.disabled) {
        return;
    }

    elements.captureButton.disabled = true;
    elements.status.textContent = 'Capturing photo.';
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    submitCanvas(canvas);
}

function handleUploadInput() {
    var input = document.getElementById('image');

    if (currentFlow !== 'upload') {
        input.value = '';
        return;
    }

    if (!input.files.length) {
        showActionScreen('Upload your photo', 'No image selected.');
        return;
    }

    capturedImageFile = null;
    sendFormData(input.files[0], input.files[0].name);
}

function useCameraInput() {
    var input = document.getElementById('camera-image');

    if (currentFlow !== 'photo') {
        input.value = '';
        return;
    }

    if (!input.files.length) {
        showActionScreen('Take your photo...', 'No photo selected.');
        return;
    }

    capturedImageFile = input.files[0];
    sendFormData(input.files[0], input.files[0].name);
}

function setTopBarStatus(message, statusType, autoClear) {
    var status = document.getElementById('topBarStatus');
    if (!status) {
        return;
    }

    clearTimeout(topBarStatusTimer);
    status.textContent = message || '';
    status.className = 'top-bar-status';

    if (statusType) {
        status.className += ' top-bar-status-' + statusType;
    }

    if (message && autoClear !== false) {
        topBarStatusTimer = setTimeout(function() {
            status.textContent = '';
            status.className = 'top-bar-status';
        }, 4000);
    }
}

function setLocationButtonBusy(isBusy) {
    var button = document.getElementById('locationButton');
    if (!button) {
        return;
    }

    button.disabled = isBusy;
    button.textContent = isBusy ? 'Finding...' : 'Use Location';
}

function locationErrorMessage(error) {
    if (error && error.code === error.PERMISSION_DENIED) {
        return 'Location permission denied.';
    }

    return 'Location unavailable. Enter town and state manually.';
}

function fillLocationFields(town, state) {
    document.getElementById('town').value = town;
    document.getElementById('state').value = state;
    saveSettings();
}

function reverseGeocodeLocation(latitude, longitude) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/reverse-geocode', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (this.readyState !== 4) {
            return;
        }

        setLocationButtonBusy(false);

        if (this.status === 200) {
            try {
                var response = JSON.parse(this.responseText);
                if (response.town && response.state) {
                    fillLocationFields(response.town, response.state);
                    setTopBarStatus('Location filled.', 'success');
                    return;
                }
            } catch (error) {
                // Fall through to the shared lookup failure message.
            }
        }

        setTopBarStatus('Location lookup failed. Enter town and state manually.', 'error');
    };
    xhr.onerror = function() {
        setLocationButtonBusy(false);
        setTopBarStatus('Location lookup failed. Enter town and state manually.', 'error');
    };
    xhr.send(JSON.stringify({
        latitude: latitude,
        longitude: longitude
    }));
}

function useDeviceLocation() {
    if (!navigator.geolocation) {
        setTopBarStatus('Location unavailable. Enter town and state manually.', 'error');
        return;
    }

    setLocationButtonBusy(true);
    setTopBarStatus('Finding location...', '', false);

    navigator.geolocation.getCurrentPosition(
        function(position) {
            reverseGeocodeLocation(position.coords.latitude, position.coords.longitude);
        },
        function(error) {
            setLocationButtonBusy(false);
            setTopBarStatus(locationErrorMessage(error), 'error');
        },
        {
            enableHighAccuracy: false,
            timeout: 10000,
            maximumAge: 600000
        }
    );
}

function saveSettings() {
    localStorage.setItem('api_key', document.getElementById('api_key').value);
    localStorage.setItem('town', document.getElementById('town').value);
    localStorage.setItem('state', document.getElementById('state').value);
    localStorage.setItem('personality', document.getElementById('personality').value);
}

function enableSettingsPersistence() {
    ['api_key', 'town', 'state', 'personality'].forEach(function(fieldId) {
        document.getElementById(fieldId).addEventListener('input', function(event) {
            localStorage.setItem(fieldId, event.target.value);
        });
    });
}

function sendFormData(imageFile, fileName) {
    if (!imageFile || isSubmitting) {
        return;
    }

    var formData = new FormData();
    formData.append('image', imageFile, fileName || imageFile.name || 'camera-photo.jpg');
    formData.append('town', document.getElementById('town').value);
    formData.append('state', document.getElementById('state').value);
    formData.append('object', document.getElementById('object').value);
    formData.append('personality', document.getElementById('personality').value);
    formData.append('api_key', document.getElementById('api_key').value);
    formData.append('model', document.getElementById('modelPicker').value);
    saveSettings();

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/process', true);
    xhr.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            var response = JSON.parse(this.responseText);
            document.getElementById('result').innerHTML = '<div id="responseHeader">' + response.header + '</div>' +
                                                            '<div id="responseDetails">' + response.details + '</div>';
            stopLoading('Ready for another photo.');
        } else if (this.readyState === 4) {
            document.getElementById('result').innerHTML = 'Error loading results. Please try again.';
            stopLoading('Something went wrong.');
        }
    };

    xhr.send(formData);
    startLoading();
}

function startLoading() {
    var elements = getFlowElements();
    var count = 0;
    isSubmitting = true;
    currentFlow = 'submitting';
    flowVersion++;
    toggleNav(1);
    stopCamera();
    elements.backButton.disabled = true;
    elements.captureButton.hidden = true;
    elements.instruction.textContent = 'Photo received';
    elements.status.textContent = 'Checking';

    clearInterval(loadingInterval);
    loadingInterval = setInterval(function() {
        if (count === 3) {
            elements.status.textContent = 'Checking';
            count = 0;
        } else {
            elements.status.textContent += '.';
            count++;
        }
    }, 500);
}

function stopLoading(statusText) {
    clearInterval(loadingInterval);
    loadingInterval = null;
    isSubmitting = false;
    currentFlow = 'result';
    flowVersion++;

    var elements = getFlowElements();
    elements.backButton.disabled = false;
    elements.instruction.textContent = 'Photo checked';
    elements.status.textContent = statusText || '';
}

function retrieveLocalStorageData() {
    var apiKey = localStorage.getItem('api_key');
    if (apiKey !== null) {
        document.getElementById('api_key').value = apiKey;
    }

    var town = localStorage.getItem('town');
    if (town !== null) {
        document.getElementById('town').value = town;
    }

    var state = localStorage.getItem('state');
    if (state !== null) {
        document.getElementById('state').value = state;
    }

    var personality = localStorage.getItem('personality');
    if (personality !== null) {
        document.getElementById('personality').value = personality;
    }
}

window.onload = function() {
    var sidebar = document.getElementById("mySidebar");
    sidebar.style.bottom = "0px";
    showChoiceScreen();
    retrieveLocalStorageData();
    enableSettingsPersistence();
    lockLayoutForFlyout();
};
