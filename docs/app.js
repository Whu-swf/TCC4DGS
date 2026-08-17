const scenes = {
  actor1_4: "actor1_4",
  actor2_3: "actor2_3",
  actor5_6: "actor5_6",
  cut_roasted_beef: "cut roasted beef",
  flame_steak: "flame steak",
  sear_steak: "sear steak",
};

const comparisonMethods = [
  {
    prefix: "STGS",
    title: "STGS",
  },
  {
    prefix: "STGS_Fastgs",
    title: "STGS + FastGS",
  },
  {
    prefix: "SpacetimeGaussians",
    title: "STGS + Ours (TCC4DGS)",
  },
  {
    prefix: "4DGaussians",
    title: "4DGaussians",
  },
  {
    prefix: "3D-4DGS",
    title: "3D-4DGS",
  },
  {
    prefix: "Ex4DGS",
    title: "Ex4DGS",
  },
];

function setupVideoCard(card) {
  if (card.dataset.videoReady === "true") return;

  const video = card.querySelector("video");
  const placeholder = card.querySelector(".video-placeholder");
  if (!video || !placeholder) return;

  const startPlayback = () => {
    if (video.hidden) return;
    const playback = video.play();
    if (playback) playback.catch(() => {});
  };
  const stopPlayback = () => video.pause();

  const showVideo = () => {
    video.hidden = false;
    placeholder.hidden = true;
    if (card.matches(":hover")) startPlayback();
  };
  const showPlaceholder = () => {
    video.hidden = true;
    placeholder.hidden = false;
  };

  video.addEventListener("loadedmetadata", showVideo, { once: true });
  video.addEventListener("error", showPlaceholder);
  video.querySelectorAll("source").forEach((source) => {
    source.addEventListener("error", showPlaceholder);
  });
  card.addEventListener("mouseenter", startPlayback);
  card.addEventListener("mouseleave", stopPlayback);
  card.dataset.videoReady = "true";
  video.load();
}

function createVideoCard(method, sceneName) {
  const sceneLabel = scenes[sceneName];
  const filename = `${method.prefix}_${sceneName}.mp4`;
  const article = document.createElement("article");
  article.className = "video-card";

  const shell = document.createElement("div");
  shell.className = "video-shell";
  shell.dataset.videoCard = "";

  const placeholder = document.createElement("div");
  placeholder.className = "video-placeholder";

  const video = document.createElement("video");
  video.controls = true;
  video.muted = true;
  video.loop = true;
  video.playsInline = true;
  video.preload = "metadata";
  video.hidden = true;
  video.setAttribute("aria-label", `${method.title} multi-view result on ${sceneLabel}`);

  const source = document.createElement("source");
  source.src = `assets/videos/comparisons/${filename}`;
  source.type = "video/mp4";
  video.append(source);

  shell.append(placeholder, video);

  const methodTitle = document.createElement("h3");
  methodTitle.className = "video-method-title";
  methodTitle.textContent = method.title;

  article.append(shell, methodTitle);
  setupVideoCard(shell);
  return article;
}

function releaseComparisonVideos(grid) {
  grid.querySelectorAll("video").forEach((video) => {
    video.pause();
    video.removeAttribute("src");
    video.querySelectorAll("source").forEach((source) => source.removeAttribute("src"));
    video.load();
  });
}

function renderScene(sceneName) {
  const grid = document.querySelector("#comparison-video-grid");
  if (!grid || !scenes[sceneName]) return;

  releaseComparisonVideos(grid);
  grid.replaceChildren(...comparisonMethods.map((method) => createVideoCard(method, sceneName)));

  document.querySelectorAll(".scene-tab").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.scene === sceneName));
  });
}

const sceneButtons = Array.from(document.querySelectorAll(".scene-tab"));
sceneButtons.forEach((button, index) => {
  button.addEventListener("click", () => renderScene(button.dataset.scene));
  button.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const offset = event.key === "ArrowRight" ? 1 : -1;
    const nextButton = sceneButtons[(index + offset + sceneButtons.length) % sceneButtons.length];
    nextButton.focus();
    nextButton.click();
  });
});

document.querySelectorAll("[data-video-card]").forEach(setupVideoCard);
renderScene("actor1_4");
