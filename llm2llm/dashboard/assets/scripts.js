(() => {
  // llm2llm/dashboard/src/state.js
  var state = {
    currentView: "conversations",
    selectedSegment: "all",
    // Conversations view
    searchTerm: "",
    filterModel: "",
    expandedConvId: null,
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
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
  function truncateText(text, maxChars, fromEnd = false) {
    if (!text) return "";
    const clean = text.replace(/^#+\s*/gm, "").replace(/\*\*([^*]+)\*\*/g, "$1").replace(/\*([^*]+)\*/g, "$1").replace(/`([^`]+)`/g, "$1").replace(/\n+/g, " ").trim();
    if (clean.length <= maxChars) return escapeHtml(clean);
    if (fromEnd) {
      const cut2 = clean.slice(-maxChars);
      const sentenceMatch = cut2.match(/^[^.!?]*[.!?]\s*/);
      if (sentenceMatch && sentenceMatch[0].length < cut2.length * 0.7) {
        return "..." + escapeHtml(cut2.slice(sentenceMatch[0].length).trim());
      }
      const firstSpace = cut2.indexOf(" ");
      const trimmed2 = firstSpace > 0 ? cut2.slice(firstSpace + 1) : cut2;
      return "..." + escapeHtml(trimmed2.trim());
    }
    const cut = clean.slice(0, maxChars);
    const lastSentenceEnd = Math.max(
      cut.lastIndexOf(". "),
      cut.lastIndexOf("! "),
      cut.lastIndexOf("? ")
    );
    if (lastSentenceEnd > maxChars * 0.3) {
      return escapeHtml(cut.slice(0, lastSentenceEnd + 1).trim());
    }
    const lastSpace = cut.lastIndexOf(" ");
    const trimmed = lastSpace > 0 ? cut.slice(0, lastSpace) : cut;
    return escapeHtml(trimmed.trim()) + "...";
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
  async function openConversation(convId, scrollToTurn = null) {
    const modal = document.getElementById("modal");
    const body = document.getElementById("modal-body");
    const conv = DATA.conversations.find((c) => c.id === convId);
    const analysis = DATA.analyses.find((a) => a.conversation_id === convId);
    if (!conv) return;
    modal.classList.remove("hidden");
    body.innerHTML = '<div style="padding: 40px; text-align: center;">Loading transcript...</div>';
    let transcript = [];
    try {
      const response = await fetch(`/conversations/${convId}.json`);
      if (response.ok) {
        const data = await response.json();
        transcript = data.messages || [];
      }
    } catch (e) {
      console.warn("Could not load transcript:", e);
    }
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
  function togglePreview(convId, event) {
    event.stopPropagation();
    state.expandedConvId = state.expandedConvId === convId ? null : convId;
    renderConversationList();
  }
  function renderPreview(convId) {
    const transcript = DATA.transcripts?.[convId] || [];
    if (transcript.length < 2) return "";
    const maxChars = 200;
    const firstTwo = transcript.slice(0, 2);
    const lastTwo = transcript.slice(-2);
    const skipped = transcript.length - 4;
    const renderSnippet = (msg, fromEnd = false) => {
      const role = msg.participant_role || "unknown";
      const roleClass = role === "initiator" ? "initiator" : "responder";
      const text = truncateText(msg.content, maxChars, fromEnd);
      return `<div class="preview-msg ${roleClass}">${text}</div>`;
    };
    const separatorText = skipped > 0 ? `${skipped} messages later` : "\xB7\xB7\xB7";
    return `
        <div class="conv-preview">
            <div class="preview-section">
                ${firstTwo.map((m) => renderSnippet(m, false)).join("")}
            </div>
            <div class="preview-separator">${separatorText}</div>
            <div class="preview-section">
                ${lastTwo.map((m) => renderSnippet(m, true)).join("")}
            </div>
        </div>
    `;
  }
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
      const isExpanded = state.expandedConvId === conv.id;
      const hasTranscript = DATA.transcripts?.[conv.id]?.length >= 2;
      html += `
            <div class="card" onclick="openConversation('${conv.id}')">
                <div class="card-title">${conv.title || "Untitled"}</div>
                <div class="card-meta">
                    <span class="model-name">${shortModel(conv.llm1_model)}</span>
                    <span>+</span>
                    <span class="model-name">${shortModel(conv.llm2_model)}</span>
                    <span>${conv.turn_count} turns</span>
                </div>
                <div class="card-tags">
                    ${topTopics.map(([t]) => `<span class="tag">${t}</span>`).join("")}
                    ${analysis?.trajectory ? `<span class="tag trajectory">${analysis.trajectory}</span>` : ""}
                </div>
                ${hasTranscript ? `
                    <div class="preview-area${isExpanded ? " expanded" : ""}" onclick="togglePreview('${conv.id}', event)">
                        <div class="preview-toggle">
                            <span class="preview-toggle-text">${isExpanded ? "hide preview" : "show preview"}</span>
                            <span class="preview-toggle-icon">${isExpanded ? "\u25B2" : "\u25BC"}</span>
                        </div>
                        ${isExpanded ? renderPreview(conv.id) : ""}
                    </div>
                ` : ""}
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

  // llm2llm/dashboard/src/views/maps.js
  var PROVIDER_COLORS = {
    anthropic: ["#8B6914", "#A67C00", "#C9A227", "#D4AF37", "#E6C55B", "#F0D77B"],
    // bronze/gold
    mistral: ["#CC5500", "#E86A17", "#FF7F2A", "#FF944D", "#FFAA70", "#FFBF94"],
    // orange
    openai: ["#10A37F", "#1DBF8E", "#3DD9A5", "#5EEDB8", "#7FFFD4", "#A0FFE0"],
    // teal/green
    google: ["#1E40AF", "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"],
    // blue (gemini)
    default: ["#6B7280", "#9CA3AF", "#D1D5DB", "#E5E7EB", "#F3F4F6", "#F9FAFB"]
    // gray
  };
  function getProvider(model) {
    if (model.startsWith("claude-")) return "anthropic";
    if (model.startsWith("mistralai/")) return "mistral";
    if (model.startsWith("gpt-")) return "openai";
    if (model.startsWith("google/")) return "google";
    return "default";
  }
  function showPairModal(pair, modelColorMap) {
    const modal = document.getElementById("modal");
    const modalBody = document.getElementById("modal-body");
    const analyses = getFilteredAnalyses().filter(
      (a) => a.llm1_model === pair.llm1_model && a.llm2_model === pair.llm2_model
    );
    const depth = avg(analyses.map((a) => a.depth ?? 0));
    const warmth = avg(analyses.map((a) => a.warmth ?? 0));
    const energy = avg(analyses.map((a) => a.energy ?? 0));
    const spirituality = avg(analyses.map((a) => a.spirituality ?? 0));
    const color1 = modelColorMap[pair.llm1_model];
    const color2 = modelColorMap[pair.llm2_model];
    modalBody.innerHTML = `
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 18px; margin-bottom: 8px;">
                <span style="color: ${color1}">${shortModel(pair.llm1_model)}</span>
                <span style="color: var(--text-muted); margin: 0 8px;">+</span>
                <span style="color: ${color2}">${shortModel(pair.llm2_model)}</span>
            </h2>
            <div style="color: var(--text-muted); font-size: 13px;">
                ${pair.conversations.length} conversation${pair.conversations.length > 1 ? "s" : ""}
            </div>
        </div>

        <div class="stats-grid" style="margin-bottom: 20px;">
            <div class="stat-card" style="background: ${metricColor("depth", depth)};">
                <div class="stat-value" style="color: ${metricTextColor("depth", depth)};">${depth.toFixed(2)}</div>
                <div class="stat-label">Depth</div>
            </div>
            <div class="stat-card" style="background: ${metricColor("warmth", warmth)};">
                <div class="stat-value" style="color: ${metricTextColor("warmth", warmth)};">${warmth.toFixed(2)}</div>
                <div class="stat-label">Warmth</div>
            </div>
            <div class="stat-card" style="background: ${metricColor("energy", energy)};">
                <div class="stat-value" style="color: ${metricTextColor("energy", energy)};">${energy.toFixed(2)}</div>
                <div class="stat-label">Energy</div>
            </div>
            <div class="stat-card" style="background: ${metricColor("spirituality", spirituality)};">
                <div class="stat-value" style="color: ${metricTextColor("spirituality", spirituality)};">${spirituality.toFixed(2)}</div>
                <div class="stat-label">Spirituality</div>
            </div>
        </div>

        <div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Conversations</div>
            ${pair.conversations.map((c) => `
                <div class="mini-card" onclick="openConversation('${c.id}')" style="margin-bottom: 6px;">
                    ${c.title || "Untitled"}
                </div>
            `).join("")}
        </div>
    `;
    modal.classList.remove("hidden");
  }
  function renderMaps(container) {
    if (!document.getElementById("map-container")) {
      container.innerHTML = `
            <div class="map-controls">
                <div class="axis-selectors">
                    <label>X axis:</label>
                    <select id="x-axis-select">
                        <option value="depth">Depth</option>
                        <option value="warmth">Warmth</option>
                        <option value="energy">Energy</option>
                        <option value="spirituality">Spirituality</option>
                    </select>
                    <label>Y axis:</label>
                    <select id="y-axis-select">
                        <option value="warmth">Warmth</option>
                        <option value="depth">Depth</option>
                        <option value="energy">Energy</option>
                        <option value="spirituality">Spirituality</option>
                    </select>
                </div>
                <div class="model-selector">
                    <label>Highlight model:</label>
                    <select id="highlight-model-select">
                        <option value="">All models</option>
                    </select>
                </div>
            </div>
            <div id="map-container">
                <svg id="scatter-plot"></svg>
                <div id="map-tooltip" class="map-tooltip hidden"></div>
            </div>
            <div id="map-legend" class="map-legend"></div>
        `;
      const modelSelect = document.getElementById("highlight-model-select");
      const models = /* @__PURE__ */ new Set();
      for (const a of DATA.analyses) {
        models.add(a.llm1_model);
        models.add(a.llm2_model);
      }
      for (const model of [...models].sort()) {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = shortModel(model);
        modelSelect.appendChild(option);
      }
      state.mapXAxis = "depth";
      state.mapYAxis = "warmth";
      state.mapHighlightModel = "";
      document.getElementById("x-axis-select").addEventListener("change", (e) => {
        state.mapXAxis = e.target.value;
        renderScatterPlot();
      });
      document.getElementById("y-axis-select").addEventListener("change", (e) => {
        state.mapYAxis = e.target.value;
        renderScatterPlot();
      });
      document.getElementById("highlight-model-select").addEventListener("change", (e) => {
        state.mapHighlightModel = e.target.value;
        renderScatterPlot();
      });
    }
    renderScatterPlot();
  }
  function renderScatterPlot() {
    const svg = document.getElementById("scatter-plot");
    const container = document.getElementById("map-container");
    const tooltip = document.getElementById("map-tooltip");
    const legend = document.getElementById("map-legend");
    if (!svg || !container) return;
    const analyses = getFilteredAnalyses();
    const xAxis = state.mapXAxis || "depth";
    const yAxis = state.mapYAxis || "warmth";
    const highlightModel = state.mapHighlightModel || "";
    const width = container.clientWidth || 800;
    const height = 500;
    const margin = { top: 20, right: 20, bottom: 50, left: 50 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);
    const allModels = /* @__PURE__ */ new Set();
    for (const a of DATA.analyses) {
      allModels.add(a.llm1_model);
      allModels.add(a.llm2_model);
    }
    const modelList = [...allModels].sort();
    const modelColorMap = {};
    const providerCounts = {};
    modelList.forEach((model) => {
      const provider = getProvider(model);
      const colors = PROVIDER_COLORS[provider] || PROVIDER_COLORS.default;
      const idx = providerCounts[provider] || 0;
      modelColorMap[model] = colors[idx % colors.length];
      providerCounts[provider] = idx + 1;
    });
    const pairMap = {};
    for (const a of analyses) {
      const pairKey = `${a.llm1_model}|${a.llm2_model}`;
      if (!pairMap[pairKey]) {
        pairMap[pairKey] = {
          llm1_model: a.llm1_model,
          llm2_model: a.llm2_model,
          conversations: [],
          xValues: [],
          yValues: []
        };
      }
      pairMap[pairKey].conversations.push({ id: a.conversation_id, title: a.title });
      pairMap[pairKey].xValues.push(a[xAxis] ?? 0);
      pairMap[pairKey].yValues.push(a[yAxis] ?? 0);
    }
    const pairAverages = Object.values(pairMap).map((pair) => ({
      pair,
      avgX: pair.xValues.reduce((a, b) => a + b, 0) / pair.xValues.length,
      avgY: pair.yValues.reduce((a, b) => a + b, 0) / pair.yValues.length
    }));
    const xValues = pairAverages.map((p) => p.avgX);
    const yValues = pairAverages.map((p) => p.avgY);
    const dataXMin = Math.min(...xValues);
    const dataXMax = Math.max(...xValues);
    const dataYMin = Math.min(...yValues);
    const dataYMax = Math.max(...yValues);
    const xPadding = (dataXMax - dataXMin) * 0.15 || 0.1;
    const yPadding = (dataYMax - dataYMin) * 0.15 || 0.1;
    const xMin = dataXMin - xPadding;
    const xMax = dataXMax + xPadding;
    const yMin = dataYMin - yPadding;
    const yMax = dataYMax + yPadding;
    const scaleX = (v) => margin.left + (v - xMin) / (xMax - xMin) * plotWidth;
    const scaleY = (v) => margin.top + plotHeight - (v - yMin) / (yMax - yMin) * plotHeight;
    let svgContent = "";
    svgContent += `<line x1="${margin.left}" y1="${margin.top + plotHeight}" x2="${margin.left + plotWidth}" y2="${margin.top + plotHeight}" stroke="var(--border)" />`;
    svgContent += `<line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + plotHeight}" stroke="var(--border)" />`;
    svgContent += `<text x="${margin.left + plotWidth / 2}" y="${height - 10}" text-anchor="middle" fill="var(--text-muted)" font-size="12">${xAxis.charAt(0).toUpperCase() + xAxis.slice(1)}</text>`;
    svgContent += `<text x="15" y="${margin.top + plotHeight / 2}" text-anchor="middle" fill="var(--text-muted)" font-size="12" transform="rotate(-90, 15, ${margin.top + plotHeight / 2})">${yAxis.charAt(0).toUpperCase() + yAxis.slice(1)}</text>`;
    const nTicks = 5;
    const xStep = (xMax - xMin) / nTicks;
    const yStep = (yMax - yMin) / nTicks;
    for (let i = 0; i <= nTicks; i++) {
      const xVal = xMin + i * xStep;
      const yVal = yMin + i * yStep;
      const x = scaleX(xVal);
      const y = scaleY(yVal);
      svgContent += `<line x1="${x}" y1="${margin.top}" x2="${x}" y2="${margin.top + plotHeight}" stroke="var(--border)" stroke-dasharray="2,2" opacity="0.5" />`;
      svgContent += `<line x1="${margin.left}" y1="${y}" x2="${margin.left + plotWidth}" y2="${y}" stroke="var(--border)" stroke-dasharray="2,2" opacity="0.5" />`;
      svgContent += `<text x="${x}" y="${margin.top + plotHeight + 15}" text-anchor="middle" fill="var(--text-muted)" font-size="10">${xVal.toFixed(2)}</text>`;
      svgContent += `<text x="${margin.left - 8}" y="${y + 4}" text-anchor="end" fill="var(--text-muted)" font-size="10">${yVal.toFixed(2)}</text>`;
    }
    const points = [];
    for (const { pair, avgX, avgY } of pairAverages) {
      const cx = scaleX(avgX);
      const cy = scaleY(avgY);
      const color1 = modelColorMap[pair.llm1_model];
      const color2 = modelColorMap[pair.llm2_model];
      let opacity = 0.9;
      let radius = 6 + Math.min(pair.conversations.length, 10);
      if (highlightModel) {
        if (pair.llm1_model === highlightModel || pair.llm2_model === highlightModel) {
          opacity = 1;
          radius += 2;
        } else {
          opacity = 0.15;
          radius = Math.max(radius - 2, 4);
        }
      }
      points.push({
        pair,
        avgX,
        avgY,
        cx,
        cy,
        color1,
        color2,
        opacity,
        radius
      });
    }
    points.sort((a, b) => a.opacity - b.opacity);
    for (const pt of points) {
      const pair = pt.pair;
      const pairId = `${pair.llm1_model}-${pair.llm2_model}`.replace(/[^a-zA-Z0-9]/g, "_");
      if (pair.llm1_model === pair.llm2_model) {
        svgContent += `<circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color1}" opacity="${pt.opacity}"
                data-pair="${pairId}" class="map-point" style="cursor: pointer;" />`;
      } else {
        svgContent += `
                <defs>
                    <clipPath id="left-${pairId}">
                        <rect x="${pt.cx - pt.radius}" y="${pt.cy - pt.radius}" width="${pt.radius}" height="${pt.radius * 2}" />
                    </clipPath>
                    <clipPath id="right-${pairId}">
                        <rect x="${pt.cx}" y="${pt.cy - pt.radius}" width="${pt.radius}" height="${pt.radius * 2}" />
                    </clipPath>
                </defs>
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color1}" opacity="${pt.opacity}" clip-path="url(#left-${pairId})"
                    data-pair="${pairId}" class="map-point" style="cursor: pointer;" />
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color2}" opacity="${pt.opacity}" clip-path="url(#right-${pairId})"
                    data-pair="${pairId}" class="map-point" style="cursor: pointer;" />
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="none" stroke="var(--border)" stroke-width="0.5" opacity="${pt.opacity}"
                    data-pair="${pairId}" class="map-point" style="cursor: pointer;" />
            `;
      }
    }
    svg.innerHTML = svgContent;
    svg.querySelectorAll(".map-point").forEach((point) => {
      point.addEventListener("mouseenter", (e) => {
        const pairId = e.target.dataset.pair;
        const pt = points.find((p) => `${p.pair.llm1_model}-${p.pair.llm2_model}`.replace(/[^a-zA-Z0-9]/g, "_") === pairId);
        if (pt) {
          const pair = pt.pair;
          tooltip.innerHTML = `
                    <div class="tooltip-models" style="margin-bottom: 8px;">
                        <span style="color: ${pt.color1}; font-weight: 600;">${shortModel(pair.llm1_model)}</span>
                        <span>\u2194</span>
                        <span style="color: ${pt.color2}; font-weight: 600;">${shortModel(pair.llm2_model)}</span>
                    </div>
                    <div class="tooltip-metrics" style="margin-bottom: 8px;">
                        ${xAxis}: ${pt.avgX.toFixed(2)} | ${yAxis}: ${pt.avgY.toFixed(2)}
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);">
                        ${pair.conversations.length} conversation${pair.conversations.length > 1 ? "s" : ""}
                    </div>
                `;
          tooltip.classList.remove("hidden");
          const rect = container.getBoundingClientRect();
          tooltip.style.left = e.clientX - rect.left + 10 + "px";
          tooltip.style.top = e.clientY - rect.top - 10 + "px";
        }
      });
      point.addEventListener("mouseleave", () => {
        tooltip.classList.add("hidden");
      });
      point.addEventListener("click", (e) => {
        const pairId = e.target.dataset.pair;
        const pt = points.find((p) => `${p.pair.llm1_model}-${p.pair.llm2_model}`.replace(/[^a-zA-Z0-9]/g, "_") === pairId);
        if (pt) {
          showPairModal(pt.pair, modelColorMap);
        }
      });
    });
    let legendHtml = '<div class="legend-title">Models</div><div class="legend-items">';
    for (const model of modelList) {
      const isHighlighted = !highlightModel || model === highlightModel;
      legendHtml += `
            <div class="legend-item ${isHighlighted ? "" : "dimmed"}" data-model="${model}" style="cursor: pointer;">
                <span class="legend-color" style="background: ${modelColorMap[model]}"></span>
                <span class="legend-label">${shortModel(model)}</span>
            </div>
        `;
    }
    legendHtml += "</div>";
    legend.innerHTML = legendHtml;
    legend.querySelectorAll(".legend-item").forEach((item) => {
      item.addEventListener("click", () => {
        const model = item.dataset.model;
        const select = document.getElementById("highlight-model-select");
        if (state.mapHighlightModel === model) {
          state.mapHighlightModel = "";
          select.value = "";
        } else {
          state.mapHighlightModel = model;
          select.value = model;
        }
        renderScatterPlot();
      });
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
  window.togglePreview = togglePreview;
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
    } else if (state.currentView === "maps") {
      if (!document.getElementById("map-container")) main.innerHTML = "";
      renderMaps(main);
    } else if (state.currentView === "insights") {
      main.innerHTML = "";
      renderInsights(main);
    }
  }
  init();
})();
