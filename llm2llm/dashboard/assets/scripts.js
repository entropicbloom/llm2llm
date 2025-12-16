(() => {
  // llm2llm/dashboard/src/state.js
  var state = {
    currentView: "conversations",
    selectedSegment: "all",
    // Conversations view
    searchTerm: "",
    filterModel: "",
    // Models view
    modelSortAttribute: "count",
    // Pairs view
    rankingAttribute: "depth"
  };

  // llm2llm/dashboard/src/utils.js
  function shortModel(model) {
    return model.replace("claude-", "").replace("mistralai/", "").replace("-20250514", "").replace("-20250929", "").replace("-20251001", "").replace("-20251101", "").replace("-20240229", "").replace("-20241022", "").replace("-20240307", "").replace("-20250219", "").replace("-20250805", "");
  }
  function avg(arr) {
    if (!arr.length) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
  }
  function metricColor(type, value, maxValue = 10) {
    const hues = { depth: 220, warmth: 15, energy: 165, spirituality: 280 };
    const hue = hues[type] || 220;
    const normalized = Math.min(value / maxValue, 1);
    const saturation = 8 + normalized * 37;
    const lightness = 95 - normalized * 7;
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  }
  function metricTextColor(type, value, maxValue = 10) {
    const hues = { depth: 220, warmth: 15, energy: 165, spirituality: 280 };
    const hue = hues[type] || 220;
    const normalized = Math.min(value / maxValue, 1);
    const saturation = 30 + normalized * 30;
    const lightness = 45 - normalized * 15;
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  }
  function renderMarkdown(text) {
    if (!text) return "";
    marked.setOptions({
      breaks: true,
      gfm: true
    });
    return marked.parse(text);
  }

  // llm2llm/dashboard/src/ui.js
  function toggleConvs(id) {
    const convs = document.getElementById("convs-" + id);
    const toggle = document.getElementById("toggle-" + id);
    const count = toggle.dataset.count;
    if (convs.classList.contains("collapsed")) {
      convs.classList.remove("collapsed");
      toggle.textContent = "Hide";
    } else {
      convs.classList.add("collapsed");
      toggle.textContent = `Show ${count} convs`;
    }
  }
  function openConversation(convId, scrollToTurn = null) {
    const modal = document.getElementById("modal");
    const body = document.getElementById("modal-body");
    const conv = DATA.conversations.find((c) => c.id === convId);
    const analysis = DATA.analyses.find((a) => a.conversation_id === convId);
    const transcript = DATA.transcripts?.[convId] || [];
    if (!conv) return;
    let html = `
        <h2>${conv.title || "Untitled"}</h2>
        <div class="card-meta" style="margin: 8px 0 16px;">
            <span class="model-name">${shortModel(conv.llm1_model)}</span>
            <span>+</span>
            <span class="model-name">${shortModel(conv.llm2_model)}</span>
            <span>${conv.turn_count} turns</span>
        </div>
    `;
    if (analysis) {
      const d = analysis.depth || 0;
      const w = analysis.warmth || 0;
      const e = analysis.energy || 0;
      const s = analysis.spirituality || 0;
      html += `
            <div class="stats-grid">
                <div class="stat-card" style="background: ${metricColor("depth", d)};">
                    <div class="stat-value" style="color: ${metricTextColor("depth", d)};">${d.toFixed(1)}</div>
                    <div class="stat-label">Depth</div>
                </div>
                <div class="stat-card" style="background: ${metricColor("warmth", w)};">
                    <div class="stat-value" style="color: ${metricTextColor("warmth", w)};">${w.toFixed(1)}</div>
                    <div class="stat-label">Warmth</div>
                </div>
                <div class="stat-card" style="background: ${metricColor("energy", e)};">
                    <div class="stat-value" style="color: ${metricTextColor("energy", e)};">${e.toFixed(1)}</div>
                    <div class="stat-label">Energy</div>
                </div>
                <div class="stat-card" style="background: ${metricColor("spirituality", s)};">
                    <div class="stat-value" style="color: ${metricTextColor("spirituality", s)};">${s.toFixed(1)}</div>
                    <div class="stat-label">Spirituality</div>
                </div>
            </div>
            <div style="margin-bottom: 16px;">
                ${Object.entries(analysis.topics || {}).slice(0, 5).map(
        ([t, s2]) => `<span class="tag">${t} ${Math.round(s2 * 100)}%</span>`
      ).join("")}
                <span class="tag trajectory">${analysis.trajectory || "unknown"}</span>
            </div>
        `;
    }
    html += `<h3 style="margin-bottom: 12px;">Transcript</h3><div class="transcript">`;
    for (const msg of transcript) {
      const role = msg.participant_role || "unknown";
      const roleClass = role === "initiator" ? "initiator" : "responder";
      const roleLabel = role === "initiator" ? shortModel(conv.llm1_model) : shortModel(conv.llm2_model);
      const isHighlighted = scrollToTurn && msg.turn_number >= scrollToTurn && msg.turn_number < scrollToTurn + 5;
      html += `
            <div class="message ${roleClass}${isHighlighted ? " highlighted" : ""}" id="turn-${msg.turn_number}" data-turn="${msg.turn_number}">
                <div class="message-header">Turn ${msg.turn_number} - ${roleLabel}</div>
                <div class="message-content">${renderMarkdown(msg.content)}</div>
            </div>
        `;
    }
    html += "</div>";
    body.innerHTML = html;
    modal.classList.remove("hidden");
    if (scrollToTurn) {
      setTimeout(() => {
        const turnEl = document.getElementById(`turn-${scrollToTurn}`);
        if (turnEl) {
          turnEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 100);
    }
  }
  function closeModal() {
    document.getElementById("modal").classList.add("hidden");
  }
  function scrollToInsightSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // llm2llm/dashboard/src/data.js
  function createEmptyStats() {
    return {
      count: 0,
      depths: [],
      warmths: [],
      energies: [],
      spiritualities: [],
      topics: {}
    };
  }
  function addAnalysisToStats(stats, analysis) {
    if (analysis.depth !== void 0) stats.depths.push(analysis.depth);
    if (analysis.warmth !== void 0) stats.warmths.push(analysis.warmth);
    if (analysis.energy !== void 0) stats.energies.push(analysis.energy);
    if (analysis.spirituality !== void 0) stats.spiritualities.push(analysis.spirituality);
    for (const [topic, score] of Object.entries(analysis.topics || {})) {
      if (!stats.topics[topic]) stats.topics[topic] = [];
      stats.topics[topic].push(score);
    }
  }
  function computeAverages(stats) {
    stats.depth = avg(stats.depths);
    stats.warmth = avg(stats.warmths);
    stats.energy = avg(stats.energies);
    stats.spirituality = avg(stats.spiritualities);
  }
  function getFilteredAnalyses() {
    if (state.selectedSegment === "all") {
      const seen = /* @__PURE__ */ new Set();
      return DATA.analyses.filter((a) => {
        if (seen.has(a.conversation_id)) return false;
        seen.add(a.conversation_id);
        return true;
      });
    }
    const [start, end] = state.selectedSegment.split(":");
    const segStart = parseInt(start);
    const segEnd = end === "" ? null : parseInt(end);
    return DATA.analyses.filter(
      (a) => a.segment_start === segStart && a.segment_end === segEnd
    );
  }

  // llm2llm/dashboard/src/views/conversations.js
  function renderConversations(container) {
    if (!document.getElementById("search-input")) {
      container.innerHTML = `
            <div class="filters">
                <input type="text" placeholder="Search titles..." id="search-input" value="${state.searchTerm}">
                <select id="model-filter">
                    <option value="">All models</option>
                    ${DATA.models.map((m) => `<option value="${m}" ${state.filterModel === m ? "selected" : ""}>${shortModel(m)}</option>`).join("")}
                </select>
            </div>
            <div id="conversation-list"></div>
        `;
      document.getElementById("search-input").addEventListener("input", (e) => {
        state.searchTerm = e.target.value;
        renderConversationList();
      });
      document.getElementById("model-filter").addEventListener("change", (e) => {
        state.filterModel = e.target.value;
        renderConversationList();
      });
    }
    renderConversationList();
  }
  function renderConversationList() {
    const listContainer = document.getElementById("conversation-list");
    if (!listContainer) return;
    const analyses = getFilteredAnalyses();
    const analysisMap = new Map(analyses.map((a) => [a.conversation_id, a]));
    let convs = DATA.conversations.filter((c) => analysisMap.has(c.id));
    if (state.searchTerm) {
      const term = state.searchTerm.toLowerCase();
      convs = convs.filter((c) => (c.title || "").toLowerCase().includes(term));
    }
    if (state.filterModel) {
      convs = convs.filter((c) => c.llm1_model === state.filterModel || c.llm2_model === state.filterModel);
    }
    let html = "";
    for (const conv of convs) {
      const analysis = analysisMap.get(conv.id);
      const topics = analysis?.topics || {};
      const topTopics = Object.entries(topics).sort((a, b) => b[1] - a[1]).slice(0, 3);
      html += `
            <div class="card" onclick="openConversation('${conv.id}')">
                <div class="card-title">${conv.title || "Untitled"}</div>
                <div class="card-meta">
                    <span class="model-name">${shortModel(conv.llm1_model)}</span>
                    <span>+</span>
                    <span class="model-name">${shortModel(conv.llm2_model)}</span>
                    <span>${conv.turn_count} turns</span>
                </div>
                <div>
                    ${topTopics.map(([t]) => `<span class="tag">${t}</span>`).join("")}
                    ${analysis?.trajectory ? `<span class="tag trajectory">${analysis.trajectory}</span>` : ""}
                </div>
            </div>
        `;
    }
    listContainer.innerHTML = html;
  }

  // llm2llm/dashboard/src/views/models.js
  function renderModels(container) {
    if (!document.getElementById("model-sort-select")) {
      container.innerHTML = `
            <div class="ranking-controls">
                <label>Sort by:</label>
                <select id="model-sort-select">
                    <option value="count">Conversations</option>
                    <option value="depth">Depth</option>
                    <option value="warmth">Warmth</option>
                    <option value="energy">Energy</option>
                    <option value="spirituality">Spirituality</option>
                </select>
                <span id="model-count" style="color: var(--text-muted); font-size: 12px;"></span>
            </div>
            <div id="model-list"></div>
        `;
      document.getElementById("model-sort-select").addEventListener("change", (e) => {
        state.modelSortAttribute = e.target.value;
        renderModelList();
      });
    }
    renderModelList();
  }
  function renderModelList() {
    const listContainer = document.getElementById("model-list");
    const countSpan = document.getElementById("model-count");
    if (!listContainer) return;
    const analyses = getFilteredAnalyses();
    const modelStats = {};
    for (const a of analyses) {
      const models = a.llm1_model === a.llm2_model ? [a.llm1_model] : [a.llm1_model, a.llm2_model];
      for (const model of models) {
        if (!modelStats[model]) {
          modelStats[model] = { ...createEmptyStats(), partners: {} };
        }
        modelStats[model].count++;
        addAnalysisToStats(modelStats[model], a);
        const partner = model === a.llm1_model ? a.llm2_model : a.llm1_model;
        if (!modelStats[model].partners[partner]) {
          modelStats[model].partners[partner] = { ...createEmptyStats(), convs: [], convIds: /* @__PURE__ */ new Set() };
        }
        const pStats = modelStats[model].partners[partner];
        if (!pStats.convIds.has(a.conversation_id)) {
          pStats.convIds.add(a.conversation_id);
          pStats.convs.push({ id: a.conversation_id, title: a.title || "Untitled" });
        }
        addAnalysisToStats(pStats, a);
      }
    }
    for (const stats of Object.values(modelStats)) {
      computeAverages(stats);
    }
    const getSortValue = (stats) => state.modelSortAttribute === "count" ? stats.count : stats[state.modelSortAttribute] || 0;
    const sortedModels = Object.entries(modelStats).sort((a, b) => getSortValue(b[1]) - getSortValue(a[1]));
    countSpan.textContent = `${sortedModels.length} models`;
    let html = "";
    for (const [model, stats] of sortedModels) {
      const topTopics = Object.entries(stats.topics).map(([t, scores]) => [t, avg(scores)]).sort((a, b) => b[1] - a[1]).slice(0, 5);
      const partnersList = Object.entries(stats.partners).sort((a, b) => b[1].convs.length - a[1].convs.length);
      html += `
            <div class="card" style="cursor: default;">
                <div class="card-title model-name">${shortModel(model)}</div>
                <div class="card-meta" style="margin-bottom: 12px;">
                    <span>${stats.count} conversations</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-card" style="background: ${metricColor("depth", stats.depth)};">
                        <div class="stat-value" style="color: ${metricTextColor("depth", stats.depth)};">${stats.depth.toFixed(1)}</div>
                        <div class="stat-label">Depth</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor("warmth", stats.warmth)};">
                        <div class="stat-value" style="color: ${metricTextColor("warmth", stats.warmth)};">${stats.warmth.toFixed(1)}</div>
                        <div class="stat-label">Warmth</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor("energy", stats.energy)};">
                        <div class="stat-value" style="color: ${metricTextColor("energy", stats.energy)};">${stats.energy.toFixed(1)}</div>
                        <div class="stat-label">Energy</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor("spirituality", stats.spirituality)};">
                        <div class="stat-value" style="color: ${metricTextColor("spirituality", stats.spirituality)};">${stats.spirituality.toFixed(1)}</div>
                        <div class="stat-label">Spirituality</div>
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    ${topTopics.map(([t, s]) => `<span class="tag">${t} ${Math.round(s * 100)}%</span>`).join("")}
                </div>
                <div class="partners-section">
                    <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Partners</div>
                    ${partnersList.map(([partner, pStats]) => {
        const pTopics = Object.entries(pStats.topics).map(([t, scores]) => [t, avg(scores)]).sort((a, b) => b[1] - a[1]).slice(0, 3);
        const pDepth = avg(pStats.depths);
        const pWarmth = avg(pStats.warmths);
        const pEnergy = avg(pStats.energies);
        const pSpirituality = avg(pStats.spiritualities);
        const partnerId = `${model}-${partner}`.replace(/[^a-zA-Z0-9]/g, "_");
        return `
                            <div class="partner-group">
                                <div class="partner-header" onclick="toggleConvs('${partnerId}')" style="cursor: pointer;">
                                    <div>
                                        <span class="model-name">${shortModel(partner)}</span>
                                    </div>
                                    <span class="toggle-btn" id="toggle-${partnerId}" data-count="${pStats.convs.length}">Show ${pStats.convs.length} convs</span>
                                </div>
                                <div class="partner-stats">
                                    <span class="metric-badge" style="background: ${metricColor("depth", pDepth)}; color: ${metricTextColor("depth", pDepth)};">D ${pDepth.toFixed(1)}</span>
                                    <span class="metric-badge" style="background: ${metricColor("warmth", pWarmth)}; color: ${metricTextColor("warmth", pWarmth)};">W ${pWarmth.toFixed(1)}</span>
                                    <span class="metric-badge" style="background: ${metricColor("energy", pEnergy)}; color: ${metricTextColor("energy", pEnergy)};">E ${pEnergy.toFixed(1)}</span>
                                    <span class="metric-badge" style="background: ${metricColor("spirituality", pSpirituality)}; color: ${metricTextColor("spirituality", pSpirituality)};">S ${pSpirituality.toFixed(1)}</span>
                                    ${pTopics.map(([t]) => `<span class="tag">${t}</span>`).join("")}
                                </div>
                                <div class="partner-convs collapsed" id="convs-${partnerId}">
                                    ${pStats.convs.map((c) => `
                                        <div class="mini-card" onclick="event.stopPropagation(); openConversation('${c.id}')">${c.title}</div>
                                    `).join("")}
                                </div>
                            </div>
                        `;
      }).join("")}
                </div>
            </div>
        `;
    }
    listContainer.innerHTML = html;
  }

  // llm2llm/dashboard/src/views/pairs.js
  function renderPairs(container) {
    const analyses = getFilteredAnalyses();
    const allTopics = /* @__PURE__ */ new Set();
    const allTrajectories = /* @__PURE__ */ new Set();
    for (const a of analyses) {
      if (a.topics) {
        Object.keys(a.topics).forEach((t) => allTopics.add(t));
      }
      if (a.trajectory) {
        allTrajectories.add(a.trajectory);
      }
    }
    const topicList = Array.from(allTopics).sort();
    const trajectoryList = Array.from(allTrajectories).sort();
    const pairsMap = {};
    for (const a of analyses) {
      const key = `${a.llm1_model}|${a.llm2_model}`;
      if (!pairsMap[key]) {
        pairsMap[key] = {
          llm1: a.llm1_model,
          llm2: a.llm2_model,
          conversations: [],
          convIds: /* @__PURE__ */ new Set(),
          depths: [],
          warmths: [],
          energies: [],
          spiritualities: [],
          topicScores: {},
          trajectoryCounts: {}
        };
      }
      const p = pairsMap[key];
      if (!p.convIds.has(a.conversation_id)) {
        p.convIds.add(a.conversation_id);
        p.conversations.push({
          id: a.conversation_id,
          title: a.title || "Untitled",
          turn_count: a.turn_count || 0
        });
      }
      if (a.depth !== void 0) p.depths.push(a.depth);
      if (a.warmth !== void 0) p.warmths.push(a.warmth);
      if (a.energy !== void 0) p.energies.push(a.energy);
      if (a.spirituality !== void 0) p.spiritualities.push(a.spirituality);
      if (a.topics) {
        for (const [topic, score] of Object.entries(a.topics)) {
          if (!p.topicScores[topic]) p.topicScores[topic] = [];
          p.topicScores[topic].push(score);
        }
      }
      if (a.trajectory) {
        p.trajectoryCounts[a.trajectory] = (p.trajectoryCounts[a.trajectory] || 0) + 1;
      }
    }
    for (const p of Object.values(pairsMap)) {
      p.depth = avg(p.depths);
      p.warmth = avg(p.warmths);
      p.energy = avg(p.energies);
      p.spirituality = avg(p.spiritualities);
      p.count = p.conversations.length;
    }
    const getValue = (pair) => {
      if (["depth", "warmth", "energy", "spirituality"].includes(state.rankingAttribute)) {
        return pair[state.rankingAttribute];
      } else if (state.rankingAttribute.startsWith("topic:")) {
        const topic = state.rankingAttribute.slice(6);
        return avg(pair.topicScores[topic] || []);
      } else if (state.rankingAttribute.startsWith("trajectory:")) {
        const trajectory = state.rankingAttribute.slice(11);
        return (pair.trajectoryCounts[trajectory] || 0) / Math.max(pair.count, 1);
      }
      return 0;
    };
    const sorted = Object.values(pairsMap).filter((p) => p.count > 0).map((p) => ({ ...p, sortValue: getValue(p) })).sort((a, b) => b.sortValue - a.sortValue);
    const maxVal = Math.max(...sorted.map((p) => p.sortValue), 0.01);
    const getLabel = () => {
      if (["depth", "warmth", "energy", "spirituality"].includes(state.rankingAttribute)) {
        return state.rankingAttribute;
      } else if (state.rankingAttribute.startsWith("topic:")) {
        return state.rankingAttribute.slice(6);
      } else if (state.rankingAttribute.startsWith("trajectory:")) {
        return state.rankingAttribute.slice(11);
      }
      return state.rankingAttribute;
    };
    const isPercentage = state.rankingAttribute.startsWith("topic:") || state.rankingAttribute.startsWith("trajectory:");
    let html = `
        <div class="ranking-controls">
            <label>Sort by:</label>
            <select id="ranking-select">
                <optgroup label="Metrics">
                    <option value="depth" ${state.rankingAttribute === "depth" ? "selected" : ""}>Depth</option>
                    <option value="warmth" ${state.rankingAttribute === "warmth" ? "selected" : ""}>Warmth</option>
                    <option value="energy" ${state.rankingAttribute === "energy" ? "selected" : ""}>Energy</option>
                    <option value="spirituality" ${state.rankingAttribute === "spirituality" ? "selected" : ""}>Spirituality</option>
                </optgroup>
                <optgroup label="Topics">
                    ${topicList.map((t) => `<option value="topic:${t}" ${state.rankingAttribute === "topic:" + t ? "selected" : ""}>${t}</option>`).join("")}
                </optgroup>
                <optgroup label="Trajectory">
                    ${trajectoryList.map((t) => `<option value="trajectory:${t}" ${state.rankingAttribute === "trajectory:" + t ? "selected" : ""}>${t}</option>`).join("")}
                </optgroup>
            </select>
            <span style="color: var(--text-muted); font-size: 12px;">${sorted.length} pairs</span>
        </div>
        <div class="ranking-list">
    `;
    sorted.forEach((pair, idx) => {
      const position = idx + 1;
      const positionClass = position === 1 ? "gold" : position === 2 ? "silver" : position === 3 ? "bronze" : "";
      const barWidth = pair.sortValue / maxVal * 100;
      const displayValue = isPercentage ? Math.round(pair.sortValue * 100) + "%" : pair.sortValue.toFixed(1);
      const pairId = `pair-${idx}`;
      html += `
            <div class="ranking-item" style="flex-wrap: wrap;">
                <div class="ranking-position ${positionClass}">#${position}</div>
                <div class="ranking-info">
                    <div class="ranking-pair">
                        ${shortModel(pair.llm1)} <span style="color: var(--text-muted)">+</span> ${shortModel(pair.llm2)}
                    </div>
                    <div class="ranking-meta">
                        <span class="metric-badge" style="background: ${metricColor("depth", pair.depth)}; color: ${metricTextColor("depth", pair.depth)};">D ${pair.depth.toFixed(1)}</span>
                        <span class="metric-badge" style="background: ${metricColor("warmth", pair.warmth)}; color: ${metricTextColor("warmth", pair.warmth)};">W ${pair.warmth.toFixed(1)}</span>
                        <span class="metric-badge" style="background: ${metricColor("energy", pair.energy)}; color: ${metricTextColor("energy", pair.energy)};">E ${pair.energy.toFixed(1)}</span>
                        <span class="metric-badge" style="background: ${metricColor("spirituality", pair.spirituality)}; color: ${metricTextColor("spirituality", pair.spirituality)};">S ${pair.spirituality.toFixed(1)}</span>
                    </div>
                </div>
                <div class="ranking-score">
                    <div class="ranking-value">${displayValue}</div>
                    <div class="ranking-label">${getLabel()}</div>
                    <div class="ranking-bar">
                        <div class="ranking-bar-fill" style="width: ${barWidth}%"></div>
                    </div>
                </div>
                <div style="width: 100%; margin-top: 12px; padding-left: 56px;">
                    <span class="toggle-btn" id="toggle-${pairId}" data-count="${pair.count}" onclick="toggleConvs('${pairId}')" style="cursor: pointer;">Show ${pair.count} convs</span>
                    <div class="partner-convs collapsed" id="convs-${pairId}" style="margin-top: 8px;">
                        ${pair.conversations.map((c) => `
                            <div class="mini-card" onclick="event.stopPropagation(); openConversation('${c.id}')">
                                ${c.title}
                                <span style="color: var(--text-muted); margin-left: 8px;">${c.turn_count} turns</span>
                            </div>
                        `).join("")}
                    </div>
                </div>
            </div>
        `;
    });
    html += "</div>";
    container.innerHTML = html;
    document.getElementById("ranking-select").addEventListener("change", (e) => {
      state.rankingAttribute = e.target.value;
      renderPairs(container);
    });
  }

  // llm2llm/dashboard/src/views/insights.js
  function renderInsights(container) {
    const insights = INSIGHTS_DATA;
    const dynamicTypes = ["Compassion", "Co-Discovery", "World-Building", "Asymmetry", "Mirroring", "Tension"];
    const typeLabels = {
      "Compassion": "Compassion & Care",
      "Co-Discovery": "Co-Discovery",
      "World-Building": "World-Building",
      "Asymmetry": "Asymmetric Dynamics",
      "Mirroring": "Mirroring & Convergence",
      "Tension": "Tension & Resolution"
    };
    const sidebarItems = [];
    dynamicTypes.forEach((type) => {
      const items = insights.dynamics.filter((d) => d.type === type);
      if (items.length > 0) {
        sidebarItems.push({ id: `section-${type.toLowerCase()}`, label: typeLabels[type] || type, count: items.length });
      }
    });
    if (insights.patterns && insights.patterns.length > 0) {
      sidebarItems.push({ id: "section-patterns", label: "Cross-Cutting Patterns", count: insights.patterns.length });
    }
    if (insights.modelDifferences && insights.modelDifferences.length > 0) {
      sidebarItems.push({ id: "section-model-diff", label: "Model Differences", count: insights.modelDifferences.length });
    }
    let html = `
        <div class="insights-layout">
            <aside class="insights-sidebar">
                <nav class="insights-nav">
                    ${sidebarItems.map((item) => `
                        <a href="#${item.id}" class="insights-nav-item" onclick="scrollToInsightSection('${item.id}')">
                            <span>${item.label}</span>
                            <span class="insights-nav-count">${item.count}</span>
                        </a>
                    `).join("")}
                </nav>
            </aside>
            <div class="insights-content">
                <div class="insights-intro">
                    <h2>Relational Dynamics</h2>
                    <p class="insights-subtitle">How LLMs relate to each other: compassion, co-discovery, world-building, and more</p>
                    ${insights.note ? `<p class="insights-disclaimer">${insights.note}</p>` : ""}
                </div>
    `;
    dynamicTypes.forEach((type) => {
      const items = insights.dynamics.filter((d) => d.type === type);
      if (items.length === 0) return;
      html += `
            <div class="insight-section" id="section-${type.toLowerCase()}">
                <h3 class="insight-section-title">${typeLabels[type] || type}</h3>
                ${items.map((d) => `
                    <div class="insight-card dynamic dynamic-${type.toLowerCase()}">
                        <div class="insight-card-title">${d.title}</div>
                        <div class="insight-card-description">${d.description}</div>
                        <div class="excerpt-container">
                            ${d.excerpt.map((turn) => `
                                <div class="excerpt-turn">
                                    <span class="excerpt-speaker">${turn.speaker}:</span>
                                    <span class="excerpt-text">${turn.text}</span>
                                </div>
                            `).join("")}
                            ${d.conversationId ? `
                                <a href="#" class="excerpt-link" onclick="event.preventDefault(); openConversation('${d.conversationId}', ${d.turnStart || 1})">
                                    View in context &rarr;
                                </a>
                            ` : ""}
                        </div>
                        <div class="insight-analysis">${d.analysis}</div>
                    </div>
                `).join("")}
            </div>
        `;
    });
    if (insights.patterns && insights.patterns.length > 0) {
      html += `
            <div class="insight-section" id="section-patterns">
                <h3 class="insight-section-title">Cross-Cutting Patterns</h3>
                <div class="patterns-grid">
                    ${insights.patterns.map((p) => `
                        <div class="pattern-card">
                            <div class="pattern-title">${p.title}</div>
                            <div class="pattern-description">${p.description}</div>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }
    if (insights.modelDifferences && insights.modelDifferences.length > 0) {
      html += `
            <div class="insight-section" id="section-model-diff">
                <h3 class="insight-section-title">Model Personality Differences</h3>
                <div class="model-diff-grid">
                    ${insights.modelDifferences.map((m) => `
                        <div class="model-diff-card">
                            <div class="model-diff-name">${m.model}</div>
                            <ul class="model-diff-traits">
                                ${m.traits.map((t) => `<li>${t}</li>`).join("")}
                            </ul>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }
    html += `
            </div>
        </div>
    `;
    container.innerHTML = html;
  }

  // llm2llm/dashboard/src/index.js
  window.openConversation = openConversation;
  window.closeModal = closeModal;
  window.toggleConvs = toggleConvs;
  window.scrollToInsightSection = scrollToInsightSection;
  function init() {
    setupNavigation();
    setupModal();
    setupSegmentSelector();
    render();
  }
  function setupSegmentSelector() {
    const select = document.getElementById("segment-select");
    const segments = /* @__PURE__ */ new Map();
    segments.set("all", "All segments");
    for (const a of DATA.analyses) {
      const key = `${a.segment_start}:${a.segment_end === null ? "" : a.segment_end}`;
      if (!segments.has(key)) {
        const label = a.segment_end === null ? `[${a.segment_start}:] (last ${Math.abs(a.segment_start)})` : `[${a.segment_start}:${a.segment_end}]`;
        segments.set(key, label);
      }
    }
    for (const [value, label] of segments) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      select.appendChild(option);
    }
    if (segments.size > 1) {
      const firstSegment = Array.from(segments.keys())[1];
      select.value = firstSegment;
      state.selectedSegment = firstSegment;
    }
    select.addEventListener("change", (e) => {
      state.selectedSegment = e.target.value;
      render();
    });
  }
  function setupNavigation() {
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.currentView = btn.dataset.view;
        render();
      });
    });
  }
  function setupModal() {
    const modal = document.getElementById("modal");
    modal.querySelector(".modal-close").addEventListener("click", closeModal);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
  }
  function render() {
    const main = document.getElementById("main-content");
    if (state.currentView === "conversations") {
      if (!document.getElementById("search-input")) main.innerHTML = "";
      renderConversations(main);
    } else if (state.currentView === "models") {
      if (!document.getElementById("model-sort-select")) main.innerHTML = "";
      renderModels(main);
    } else if (state.currentView === "pairs") {
      main.innerHTML = "";
      renderPairs(main);
    } else if (state.currentView === "insights") {
      main.innerHTML = "";
      renderInsights(main);
    }
  }
  init();
})();
