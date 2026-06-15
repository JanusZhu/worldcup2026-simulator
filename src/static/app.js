const groupSelect = document.querySelector("#groupSelect");
const matchSelect = document.querySelector("#matchSelect");
const simulateButton = document.querySelector("#simulateButton");
const result = document.querySelector("#result");

let groups = [];

const percent = (value) => `${(value * 100).toFixed(1)}%`;
const fixed = (value) => Number(value).toFixed(2);

function flagImage(team) {
  if (!team.flag_url) return `<div class="flag placeholder"></div>`;
  return `<img class="flag" src="${team.flag_url}" alt="${team.name} 国旗" onerror="this.style.visibility='hidden'" />`;
}

function statRow(label, value) {
  return `<div class="stat-row"><span>${label}</span><strong>${value}</strong></div>`;
}

function teamPanel(team) {
  const host = team.is_host ? `<span class="host-tag">Host</span>` : "";
  return `
    <article class="team-panel">
      <div class="team-heading">
        ${flagImage(team)}
        <div>
          <h2>${team.name}</h2>
          <p>${team.confederation} ${host}</p>
        </div>
      </div>
      <div class="team-stats">
        ${statRow("Elo", Math.round(team.elo))}
        ${statRow("Attack", fixed(team.attack))}
        ${statRow("Defense", fixed(team.defense))}
      </div>
    </article>
  `;
}

function matchMeta(schedule, actualProbability) {
  if (!schedule) {
    return `
      <section class="match-meta">
        <div>
          <span>赛程信息</span>
          <strong>暂无外部赛程数据</strong>
        </div>
      </section>
    `;
  }
  const status = schedule.is_played ? "已结束" : "未开始";
  const score = schedule.is_played
    ? `<div><span>实际比分</span><strong>${schedule.actual_score}</strong></div>`
    : "";
  const modelProb = schedule.is_played && actualProbability !== null && actualProbability !== undefined
    ? `<div><span>实际比分模型概率</span><strong>${percent(actualProbability)}</strong></div>`
    : "";
  return `
    <section class="match-meta">
      <div><span>状态</span><strong>${status}</strong></div>
      <div><span>日期</span><strong>${schedule.date || "-"}</strong></div>
      <div><span>时间</span><strong>${schedule.time || "-"}</strong></div>
      <div><span>地点</span><strong>${schedule.ground || "-"}</strong></div>
      ${score}
      ${modelProb}
    </section>
  `;
}

function probabilityBar(label, value, className) {
  return `
    <div class="probability-row">
      <div class="probability-label">
        <span>${label}</span>
        <strong>${percent(value)}</strong>
      </div>
      <div class="bar-track">
        <div class="bar-fill ${className}" style="width: ${value * 100}%"></div>
      </div>
    </div>
  `;
}

function scoreTable(scores) {
  return `
    <table>
      <thead>
        <tr>
          <th>比分</th>
          <th>概率</th>
          <th>次数</th>
        </tr>
      </thead>
      <tbody>
        ${scores.map((score) => `
          <tr>
            <td>${score.score}</td>
            <td>${percent(score.probability)}</td>
            <td>${score.count}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderResult(data) {
  result.innerHTML = `
    <div class="match-layout">
      ${teamPanel(data.team_a)}
      <section class="scoreline">
        <div class="scoreline-label">Expected Goals</div>
        <div class="xg">
          <span>${fixed(data.expected_goals_a)}</span>
          <b>-</b>
          <span>${fixed(data.expected_goals_b)}</span>
        </div>
        <p>${data.team_a.name} vs ${data.team_b.name}</p>
      </section>
      ${teamPanel(data.team_b)}
    </div>

    ${matchMeta(data.schedule, data.actual_score_probability)}

    <section class="dashboard-grid">
      <article class="panel">
        <h3>胜平负概率</h3>
        ${probabilityBar(`${data.team_a.name} 胜`, data.team_a_win_prob, "home")}
        ${probabilityBar("平局", data.draw_prob, "draw")}
        ${probabilityBar(`${data.team_b.name} 胜`, data.team_b_win_prob, "away")}
      </article>

      <article class="panel">
        <h3>最可能比分</h3>
        ${scoreTable(data.top_scores)}
      </article>
    </section>

    <section class="explanation">
      <h3>结果解释</h3>
      <p>${data.explanation}</p>
    </section>
  `;
}

function renderLoading() {
  result.innerHTML = `<div class="empty-state">正在模拟 10,000 次比赛...</div>`;
}

function renderError(message) {
  result.innerHTML = `<div class="empty-state error">${message}</div>`;
}

function updateMatchOptions() {
  const group = groups.find((item) => item.group === groupSelect.value);
  matchSelect.innerHTML = "";
  group.matches.forEach((match) => {
    const option = document.createElement("option");
    option.value = JSON.stringify({ team_a: match.team_a, team_b: match.team_b });
    option.textContent = match.label;
    matchSelect.appendChild(option);
  });
}

async function loadGroups() {
  const response = await fetch("/api/groups");
  const data = await response.json();
  groups = data.groups;
  groups.forEach((group) => {
    const option = document.createElement("option");
    option.value = group.group;
    option.textContent = `Group ${group.group}`;
    groupSelect.appendChild(option);
  });
  updateMatchOptions();
}

async function simulateSelectedMatch() {
  renderLoading();
  const match = JSON.parse(matchSelect.value);
  const response = await fetch("/api/simulate-match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(match),
  });
  const data = await response.json();
  if (!response.ok) {
    renderError(data.error || "模拟失败，请重新选择比赛。");
    return;
  }
  renderResult(data);
}

groupSelect.addEventListener("change", updateMatchOptions);
simulateButton.addEventListener("click", simulateSelectedMatch);

loadGroups().catch(() => renderError("小组数据加载失败。"));
