console.log("E-Voting System Loaded");

/* ================================
   REGISTER
================================ */
function registerUser() {
  if (!fingerprintVerified) {
  alert("⚠ Please verify fingerprint first!");
  return;
}

  fetch("http://127.0.0.1:5000/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      name: document.getElementById("regName").value,
      cnic: document.getElementById("regCnic").value,
      email: document.getElementById("regEmail").value,
      password: document.getElementById("regPassword").value
    })
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message);
    if(data.message === "Registration Successful"){
      window.location.href = "login.html";
    }
  })
  .catch(err => console.log(err));
}


/* ================================
   LOGIN
================================ */
function loginUser() {
  if (!loginFingerprintVerified) {
  alert("⚠ Please verify fingerprint first!");
  return;
}
  fetch("http://127.0.0.1:5000/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      email: document.getElementById("loginEmail").value,
      password: document.getElementById("loginPassword").value
    })
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message);
    if(data.message === "Login Successful"){
      localStorage.setItem("user", document.getElementById("loginEmail").value);
      window.location.href = "vote.html";
    }
  });
}


/* ================================
   VOTE
================================ */
function castVote(candidate) {
  let email = localStorage.getItem("user");

  fetch("http://127.0.0.1:5000/vote", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      email: email,
      candidate: candidate
    })
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message);

    if(data.message === "Vote Cast Successfully"){
      document.getElementById("vote-success").style.display = "block";
    }
  });
}


/* ================================
   RESULTS
================================ */
let chart; // global variable

function loadResults() {
  fetch("http://127.0.0.1:5000/results")
    .then(res => res.json())
    .then(data => {

      let names = data.map(c => c.name);
      let votes = data.map(c => c.votes);

      // TEXT RESULTS
      let output = "";
      data.forEach(c => {
        output += `<p>${c.name}: ${c.votes}</p>`;
      });
      document.getElementById("results").innerHTML = output;

      // GRAPH
      let ctx = document.getElementById("chart").getContext("2d");

      if (chart) {
        chart.destroy(); // old chart remove
      }

      chart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: names,
          datasets: [{
            label: "Votes",
            data: votes
          }]
        },
        options: {
          responsive: true
        }
      });

    });
}

window.onload = loadResults;
setInterval(loadResults, 3000);


function loadAdminData() {

  // RESULTS
  fetch("http://127.0.0.1:5000/results")
    .then(res => res.json())
    .then(data => {
      let output = "";
      data.forEach(c => {
        output += `<p>${c.name}: ${c.votes}</p>`;
      });
      document.getElementById("adminResults").innerHTML = output;
    });

  // VOTERS
  fetch("http://127.0.0.1:5000/admin/voters")
    .then(res => res.json())
    .then(data => {
      let output = "";
      data.forEach(v => {
        output += `<p>${v.name} (${v.email}) - ${v.hasVoted ? "Voted" : "Not Voted"}</p>`;
      });
      document.getElementById("votersList").innerHTML = output;
    });
}

function resetVotes() {
  fetch("http://127.0.0.1:5000/admin/reset", {
    method: "POST"
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message);
    loadAdminData();
  });
}

let fingerprintVerified = false;

function verifyFingerprint() {
  alert("🔐 Place your finger on scanner...");

  // future me real device yahan connect hoga
  setTimeout(() => {
    fingerprintVerified = true;

    document.getElementById("fingerprint-status").innerText =
      "🟢 Fingerprint Verified";

    document.getElementById("fingerprint-status").style.color = "#00ff9c";

    // REGISTER BUTTON ENABLE
    document.getElementById("registerBtn").disabled = false;

  }, 1500);
}
let loginFingerprintVerified = false;

function verifyLoginFingerprint(){
  document.getElementById("login-fingerprint-status").innerText = "⏳ Scanning...";

  setTimeout(() => {
    loginFingerprintVerified = true;
    document.getElementById("login-fingerprint-status").innerText = "✅ Verified";
  }, 1500);
}