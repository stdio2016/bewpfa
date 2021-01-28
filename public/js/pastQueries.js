function toplay() {
  var btn = event.target;
  var cell = btn.parentElement;
  var src = btn.dataset.src;
  btn.remove();
  var audio = new Audio('wavs/' + src + '.wav');
  audio.controls = true;
  cell.append(audio);
  audio.play();
}

function showResult(json) {
  var songs = json.songs;
  if (!(songs instanceof Array)) return;
  var table = document.querySelector('.query-results table tbody');
  console.log(table);
  while (table.rows.length > 0) {
    table.rows[0].remove();
  }
  for (var i = 0; i < songs.length; i++) {
    var row = table.insertRow(i);
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    cell1.textContent = songs[i].name;
    cell2.textContent = songs[i].score;
    cell2.style.textAlign = 'center';
    var audio = new Audio();
    audio.preload = 'none';
    if (songs[i].file)
      audio.src = songs[i].file;
    else
      audio.src = '/finddup/audio/' + songs[i].name;
    if (songs[i].time)
      audio.currentTime = songs[i].time;
    audio.controls = true;
    cell3.append(audio);
  }
}

function parseQuery() {
  var search = location.search;
  var args = {};
  search = search.substring(1).split('&');
  for (var i = 0; i < search.length; i++) {
    var find = search[i].indexOf('=');
    var name = search[i], dat = '';
    if (find != -1) {
      var name = search[i].substring(0, find);
      var dat = search[i].substring(find+1);
    }
    args[name] = dat;
  }
  console.log(args);
  return args;
}

function loadDetails() {
  var args = parseQuery();
  if (!args.name) return;
  
  audioElt.src = 'wavs/' + args.name + '.wav';
  
  var xhr = new XMLHttpRequest();
  xhr.onload = function () {
    var json = JSON.parse(xhr.responseText);
    showResult(json);
  }
  xhr.open('GET', 'queryResult/' + args.name);
  xhr.send();
}
