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
