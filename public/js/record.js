window.AudioContext = window.AudioContext || window.webkitAudioContext;
var audioCtx = new AudioContext();
var audioStream = null;
var audioStreamNode = null;
var intercept = audioCtx.createScriptProcessor();
var recording = false;
var querySecs = 10;
var buffer = new Float32Array(audioCtx.sampleRate * querySecs);
var canvas = document.querySelector('canvas.visualizer');
var bufferPos = 0;
var rafId;
var visualizeX = 0;
var wavFile = null;
var waitId = '';
var queryResult;

intercept.onaudioprocess = function (e) {
  if (recording) {
    var dat = e.inputBuffer.getChannelData(0);
    var pos = bufferPos;
    var nonzero = false;
    for (var i = 0; i < dat.length; i++) {
      buffer[pos] = dat[i];
      pos += 1;
      if (dat[i]) nonzero = true;
    }
    if (nonzero || bufferPos > 0) {
      bufferPos = pos;
    }
    if (bufferPos >= buffer.length) setTimeout(stopRecord, 0);
  }
};

intercept.connect(audioCtx.destination);

function startup() {
  btnRecord.disabled = false;
  btnRecord.onclick = startRecord;
  btnStop.disabled = true;
}

function tryToGetRecorder() {
  var needs = {
    "audio": {
    }
  };

  function onSuccess(stream) {
    try {
      audioStream = stream;
      audioStreamNode = audioCtx.createMediaStreamSource(stream);
      audioStreamNode.connect(intercept);
      startRecord();
    }
    catch (e) {
      alert(e);
    }
  }

  function onFailure(err) {
    switch (err.name) {
      case "SecurityError":
        alert("Your browser does not allow the use of UserMedia");
        break;
      case "NotAllowedError":
        alert("You don't allow browser to access microphone.\n(You can refresh this page and try again)");
        break;
      case "OverconstrainedError":
        alert("It seems that your device doesn't have a mic, or the browser just doesn't support it.");
        break;
      default:
        alert("The following error occured: " + err);
    }
  }

  navigator.mediaDevices.getUserMedia(needs).then(onSuccess, onFailure);
};

function startRecord() {
  audioCtx.resume();
  if (!audioStream) {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      tryToGetRecorder();
    }
    else {
      alert("Your browser does not support audio recording");
    }
    return;
  }
  btnStop.disabled = false;
  btnStop.onclick = stopRecord;
  btnRecord.disabled = true;
  recording = true;
  bufferPos = 0;
  buffer = new Float32Array(audioCtx.sampleRate * querySecs);
  visualizeX = 0;
  rafId = requestAnimationFrame(visualize);

  var ctx = canvas.getContext('2d');
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function visualize() {
  var ctx = canvas.getContext('2d');
  var h = canvas.height * 0.5;
  var w = canvas.width;
  ctx.beginPath();
  var x;
  for (x = visualizeX; x < w; x++) {
    var pos = Math.floor(buffer.length * x / w);
    var pos2 = Math.floor(buffer.length * (x+1) / w);
    if (pos2 > bufferPos) break;
    var y = 0;
    for (var i = pos; i < pos2; i++) {
      y = Math.max(y, Math.abs(buffer[i]));
    }
    ctx.moveTo(x, h * (1 - y));
    ctx.lineTo(x, h * (1 + y));
  }
  ctx.stroke();
  visualizeX = x;
  rafId = requestAnimationFrame(visualize);
}

function stopRecord() {
  if (recording) {
    cancelAnimationFrame(rafId);
    btnStop.disabled = true;
    recording = false;
    showProgress('Encoding', '25%');
    setTimeout(function () {
      try {
        encodeWav();
      }
      catch (x) {
        alert(x);
        ended();
      }
    }, 4);
  }
}

function showProgress(msg, percent) {
  var pro = document.querySelector('.progress');
  pro.style.visibility = 'visible';
  prom = document.getElementById('progressMessage');
  prom.textContent = msg;
  pc = document.querySelector('.progress-bar');
  pc.style.width = percent;
}

function encodeWav() {
  var sampleRate = audioCtx.sampleRate;
  var channels = 1;
  var bps = 16;
  var compression = 5;
  var verify = false;
  var blockSize = 0;
  var flac_encoder = Flac.create_libflac_encoder(sampleRate, channels, bps, compression, 0, verify, blockSize);
  var result = [];

  function write_callback_fn(encodedData, bytes, samples, current_frame) {
    result.push(encodedData);
  }
  function metadata_callback_fn() {
    
  }
  Flac.init_encoder_ogg_stream(flac_encoder,
    write_callback_fn,    //required callback(s)
    metadata_callback_fn  //optional callback(s)
  );
  var buf_length = Math.min(buffer.length, bufferPos);
  var buffer_i32 = new Int32Array(buf_length);
  var view = new DataView(buffer_i32.buffer);
  for (var i = 0; i < buf_length; i++) {
    view.setInt32(i*4, buffer[i] * 0x7fff, true);
  }
  Flac.FLAC__stream_encoder_process_interleaved(flac_encoder, buffer_i32, buf_length);
  Flac.FLAC__stream_encoder_finish(flac_encoder);
  Flac.FLAC__stream_encoder_delete(flac_encoder);
  wavFile = new Blob(result);
  console.log(wavFile.size);
  showProgress('Uploading', '50%');
  uploadWav(wavFile);
}

function uploadWav(blob) {
  var xhr = new XMLHttpRequest();
  xhr.open('POST', 'query');
  var formData = new FormData();
  formData.append('file', blob);
  xhr.send(formData);
  xhr.onload = function () {
    if (xhr.status == 200) {
      console.log(xhr.response);
      showProgress('Processing result', '100%');
      waitId = xhr.response;
      waitResult(xhr.response, +new Date());
    }
    else {
      alert('Server error: ' + xhr.status + ' ' + xhr.statusText);
      ended();
    }
  };
  xhr.onerror = function () {
    alert('upload failed');
    ended();
  };
}

function waitResult(id, startTime) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', 'queryResult/' + id);
  xhr.send();
  xhr.onload = function () {
    if (xhr.status == 200) {
      try {
        queryResult = JSON.parse(xhr.response);
        console.log(queryResult);
        if (queryResult.progress == 100) {
          ended();
        }
        else if (queryResult.progress == 'error') {
          alert('Server error!');
          ended();
        }
        else if (new Date() - startTime > 10000) {
          alert('Server timeout');
          ended();
        }
        else {
          setTimeout(waitResult.bind(this, id, startTime), 100);
        }
      }
      catch (x) {
        alert('Server malfunction: ' + x);
        ended();
      }
    }
    else {
      alert('Server error: ' + xhr.status + ' ' + xhr.statusText);
      ended();
    }
  };
  xhr.onerror = function () {
    alert('Server is down!');
    ended();
  };
}

function ended() {
  showProgress('', '0%');
  btnRecord.disabled = false;
}

Flac.on('ready', function(event){
  startup();
});
