function toggleNav(special = 0) {
    var sidebar = document.getElementById("mySidebar");
    //Special close
    if (special==1) {
        sidebar.style.bottom = "-320px"; // Hide the sidebar
    }

    //Special open
    else if (special==2) {
        sidebar.style.bottom = "0px"; // Hide the sidebar
    }

    else if (sidebar.style.bottom === "0px") {
        sidebar.style.bottom = "-320px"; // Hide the sidebar
    }
    else {
        sidebar.style.bottom = "0px"; // Show the sidebar
    }
}

function updateFileName() {
    var input = document.getElementById('image');
    if (!input.files.length) {
        return;
    }
    capturedImageFile = null;
    document.getElementById('file-name').textContent = input.files[0].name;
    toggleNav(2);
}

var capturedImageFile = null;
var cameraStream = null;

function setSelectedImage(file, fileName) {
    capturedImageFile = file;
    document.getElementById('image').value = '';
    document.getElementById('file-name').textContent = fileName;
    toggleNav(2);
}

function useCameraInput() {
    var input = document.getElementById('camera-image');
    if (input.files.length) {
        setSelectedImage(input.files[0], input.files[0].name);
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(function(track) {
            track.stop();
        });
        cameraStream = null;
    }

    document.getElementById('camera-preview').hidden = true;
    document.getElementById('cancelCameraButton').hidden = true;
    document.getElementById('takePhotoButton').textContent = 'Take Photo';
    document.getElementById('takePhotoButton').disabled = false;
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

function saveCapturedCanvas(canvas) {
    var fileName = 'camera-photo.jpg';
    var saveBlob = function(blob) {
        if (!blob) {
            document.getElementById('result').innerHTML = 'Could not capture photo. Please try again.';
            return;
        }

        setSelectedImage(blob, fileName);
        stopCamera();
    };

    if (canvas.toBlob) {
        canvas.toBlob(saveBlob, 'image/jpeg', 0.9);
    } else {
        saveBlob(dataUrlToBlob(canvas.toDataURL('image/jpeg', 0.9)));
    }
}

function takePhoto() {
    var video = document.getElementById('camera-preview');
    var canvas = document.getElementById('camera-canvas');
    var takeButton = document.getElementById('takePhotoButton');
    var cancelButton = document.getElementById('cancelCameraButton');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        document.getElementById('camera-image').click();
        return;
    }

    if (!cameraStream) {
        takeButton.textContent = 'Opening Camera';
        takeButton.disabled = true;
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(function(stream) {
                cameraStream = stream;
                video.srcObject = stream;
                video.hidden = false;
                cancelButton.hidden = false;
                takeButton.textContent = 'Capture Photo';
                takeButton.disabled = false;
            })
            .catch(function() {
                takeButton.textContent = 'Take Photo';
                takeButton.disabled = false;
                document.getElementById('camera-image').click();
            });
        return;
    }

    if (!video.videoWidth || !video.videoHeight) {
        document.getElementById('result').innerHTML = 'Camera is starting. Please try again in a moment.';
        return;
    }

    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    saveCapturedCanvas(canvas);
}

function sendFormData() {
    var uploadedFile = document.getElementById('image').files[0];
    var imageFile = capturedImageFile || uploadedFile;

    if (!imageFile) {
        document.getElementById('result').innerHTML = 'Please upload an image or take a photo first.';
        return;
    }

    var formData = new FormData();
    formData.append('image', imageFile, imageFile.name || 'camera-photo.jpg');
    formData.append('town', document.getElementById('town').value);
    formData.append('state', document.getElementById('state').value);
    formData.append('object', document.getElementById('object').value);
    formData.append('personality', document.getElementById('personality').value);
    formData.append('api_key', document.getElementById('api_key').value); // Append the API key

    var apiKey = document.getElementById('api_key').value;
    localStorage.setItem('api_key', apiKey);
    var save_town = document.getElementById('town').value;
    localStorage.setItem('town', save_town);
    var save_state = document.getElementById('state').value;
    localStorage.setItem('state', save_state);
    var save_personality = document.getElementById('personality').value;
    localStorage.setItem('personality', save_personality);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/process', true);
    xhr.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            var response = JSON.parse(this.responseText);
            // Update the result div with the response data
            document.getElementById('result').innerHTML = '<div id="responseHeader">' + response.header + '</div>' +
                                                            '<div id="responseDetails">' + response.details + '</div>';
            stopLoading(); // Call this to stop loading indication
        } else if (this.readyState === 4) {
            // Handle errors (e.g., server errors, network issues)
            document.getElementById('result').innerHTML = "Error loading results. Please try again.";
            stopLoading();
        }
    };
    xhr.send(formData);
    startLoading(); // Call this to start loading indication
}

var loadingInterval; // Declare this outside so it can be cleared later

function startLoading() {
    toggleNav(1); // Hide the sidebar
    
    var button = document.getElementById('checkButton');
    button.innerHTML = 'Loading';
    var count = 0;

    loadingInterval = setInterval(function() {
        if (count === 3) {
            button.innerHTML = 'Loading';
            count = 0;
        } else {
            button.innerHTML += '.';
            count++;
        }
    }, 500); // Change text every 500 milliseconds
}

// Function to stop the loading
function stopLoading() {
    clearInterval(loadingInterval);
    var button = document.getElementById('checkButton');
    button.innerHTML = 'Check';
}

function retrieveLocalStorageData() {
    // Retrieve each value from localStorage and set it to the corresponding input field
    var apiKey = localStorage.getItem('api_key');
    if (apiKey) {
        document.getElementById('api_key').value = apiKey;
    }

    var town = localStorage.getItem('town');
    if (town) {
        document.getElementById('town').value = town;
    }

    var state = localStorage.getItem('state');
    if (state) {
        document.getElementById('state').value = state;
    }

    var personality = localStorage.getItem('personality');
    if (personality) {
        document.getElementById('personality').value = personality;
    }
}


window.onload = function() {
    var savedApiKey = localStorage.getItem('api_key');
    if (savedApiKey) {
        document.getElementById('api_key').value = savedApiKey;
    }
    var sidebar = document.getElementById("mySidebar");
    sidebar.style.bottom = "0px"; // Or "0px" if you want it to be open initially
    if (document.getElementById('result')) {
        stopLoading();
    }

    retrieveLocalStorageData(); // Retrieve and display localStorage data on window load
};

function clearData() {
    localStorage.removeItem('api_key');
    localStorage.removeItem('town');
    localStorage.removeItem('state');
    localStorage.removeItem('personality');

    document.getElementById('api_key').value = '';
    document.getElementById('town').value = ''; // Also clear the input field
    document.getElementById('state').value = '';
    document.getElementById('personality').value = '';

    // Show the cleared banner
    var banner = document.getElementById('clearedBanner');
    banner.style.display = 'block';

    // Hide the banner after a few seconds
    setTimeout(function() {
        banner.style.display = 'none';
    }, 3000); // Adjust the time as needed
}
