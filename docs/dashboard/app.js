(function () {
  const data = window.GDL_PUBLIC;
  if (!data) return;

  const formatInt = (value) =>
    Math.round(Number(value)).toLocaleString("ko-KR");

  const formatSigned = (value) => {
    const number = Math.round(Number(value));
    const body = Math.abs(number).toLocaleString("ko-KR");
    if (number > 0) return "+" + body;
    if (number < 0) return "−" + body;
    return "0";
  };

  const formatCard = (card) => {
    if (card.format === "gbp") return "£" + formatInt(card.value);
    if (card.format === "pct") return (Number(card.value) * 100).toFixed(1) + "%";
    if (card.format === "number") return Number(card.value).toFixed(2);
    if (card.format === "count") return formatInt(card.value);
    if (card.format === "signed") return formatSigned(card.value);
    return formatInt(card.value);
  };

  const renderCards = (node, cards) => {
    node.innerHTML = cards
      .map((card) => {
        const value = formatCard(card);
        return (
          '<article class="card">' +
          '<p class="label">' + card.label + "</p>" +
          '<p class="value">' + value + "</p>" +
          '<p class="note">' + card.note + "</p>" +
          "</article>"
        );
      })
      .join("");
  };

  const renderBars = (node, rows, options) => {
    const max = Math.max(...rows.map((row) => Math.abs(row.value)), 1);
    node.innerHTML = rows
      .map((row, index) => {
        const width = (Math.abs(row.value) / max) * 100;
        const kind = row.value > 0 ? "plus" : row.value < 0 ? "minus" : "neutral";
        const label = options.signed ? formatSigned(row.value) : formatInt(row.value);
        const tag = options.clickable ? "button" : "div";
        const extra = options.clickable
          ? ' type="button" data-index="' + index + '"'
          : " disabled";
        return (
          "<" + tag + ' class="bar-row"' + extra + ">" +
          '<span class="name">' + row.name + "</span>" +
          '<span class="track"><span class="fill ' + kind + '" style="width:' + width + '%"></span></span>' +
          '<span class="num">' + label + "</span>" +
          "</" + tag + ">"
        );
      })
      .join("");
  };

  const showSido = (index) => {
    const row = data.case02.youth_profile[index];
    const detail = document.getElementById("sido-detail");
    detail.innerHTML =
      "<h3>" + row.sido + '</h3>' +
      '<span class="badge">' + row.typology_ko + "</span>" +
      "<dl>" +
      "<div><dt>청년 20–39</dt><dd>" + formatSigned(row.net_youth) + "</dd></div>" +
      "<div><dt>20대</dt><dd>" + formatSigned(row.net_20s) + "</dd></div>" +
      "<div><dt>30대</dt><dd>" + formatSigned(row.net_30s) + "</dd></div>" +
      "<div><dt>전체 연령</dt><dd>" + formatSigned(row.net_total) + "</dd></div>" +
      "</dl>" +
      '<p class="hint">청년 합과 전체 연령 부호가 다를 수 있습니다. 서울이 그 예입니다.</p>';

    document.querySelectorAll("#sido-bars .bar-row").forEach((el, i) => {
      el.classList.toggle("is-selected", i === index);
    });
  };

  const start = () => {
    const case02 = data.case02;
    const case01 = data.case01;
    document.getElementById("case02-title").textContent = case02.title;
    document.getElementById("case01-title").textContent = case01.title;
    document.getElementById("case01-period").textContent =
      case01.period + " · RFM 기준일 " + case01.snapshot_date;

    renderCards(document.getElementById("case02-cards"), case02.cards);
    renderCards(document.getElementById("case01-cards"), case01.cards);

    const sidoRows = case02.youth_profile
      .slice()
      .sort((a, b) => b.net_youth - a.net_youth)
      .map((row) => ({ name: row.sido, value: row.net_youth, raw: row }));

    data.case02.youth_profile = sidoRows.map((row) => row.raw);
    renderBars(document.getElementById("sido-bars"), sidoRows, {
      signed: true,
      clickable: true,
    });
    document.getElementById("sido-bars").addEventListener("click", (event) => {
      const button = event.target.closest("[data-index]");
      if (!button) return;
      showSido(Number(button.dataset.index));
    });
    const seoul = sidoRows.findIndex((row) => row.name === "서울");
    showSido(seoul === -1 ? 0 : seoul);

    document.getElementById("typology").innerHTML = case02.typology
      .map((row) => (
        '<div class="type" data-type="' + row.typology + '">' +
        "<strong>" + row.typology_ko + " · " + row.sido_count + "곳</strong>" +
        "<span>" + row.sidos + "</span>" +
        "</div>"
      ))
      .join("");

    renderBars(
      document.getElementById("od-bars"),
      case02.top_od.map((row) => ({
        name: row.origin + "→" + row.destination,
        value: row.movers,
      })),
      { signed: false, clickable: false }
    );

    renderBars(
      document.getElementById("segment-bars"),
      case01.segments
        .slice()
        .sort((a, b) => b.revenue - a.revenue)
        .map((row) => ({ name: row.segment, value: row.revenue })),
      { signed: false, clickable: false }
    );

    document.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((el) => el.classList.remove("is-active"));
        document.querySelectorAll(".panel").forEach((el) => el.classList.remove("is-active"));
        tab.classList.add("is-active");
        document.getElementById(tab.dataset.tab).classList.add("is-active");
      });
    });
  };

  start();
})();
