export interface NavItem {
  readonly label: string;
  readonly href: string;
  readonly external?: boolean;
}

export interface FeaturePillar {
  readonly id: "offline" | "explorer" | "verified";
  readonly title: string;
  readonly description: string;
}

export interface FaqEntry {
  readonly id: string;
  readonly question: string;
  readonly answer: string;
}

export interface CliCommandExample {
  readonly id: string;
  readonly label: string;
  readonly command: string;
}

const GITHUB_URL = "https://github.com/fadhiilahahmadzikri/mortemtrimmer";
const SITE_URL = "https://mortemtrimmer.pages.dev";
const RELEASE_VERSION = "1.1.0";
const INSTALLER_FILENAME = `MortemTrimmer-Setup-${RELEASE_VERSION}-win-x64.exe`;

export const SITE_CONFIG = {
  name: "Mortem Trimmer",
  wordmark: "MORTEM TRIMMER",
  siteUrl: SITE_URL,
  logoPath: "/mortem-logo.png",
  logoWidth: 1024,
  logoHeight: 259,
  iconPath: "/mortem-icon.png",
  heroBgPath: "/hero-knight-bg.jpg",
  heroBgWidth: 1672,
  heroBgHeight: 941,
  ogImagePath: "/og-image.jpg",
  ogImageWidth: 1200,
  ogImageHeight: 630,
  ogImageAlt:
    "Mortem Trimmer — Automate Video Silence Trimming Offline on Windows",
  tagline:
    "Self-Contained Offline AI Silence Remover & Noise Reduction Production Suite for Windows.",
  seoTitle:
    "Mortem Trimmer — How to Automate Video Silence Trimming Offline on Windows",
  seoDescription:
    "Automatically detect and trim silent pauses from video and audio 100% offline using Silero VAD, Faster-Whisper, and DeepFilterNet3. Windows Explorer right-click & CLI.",
  keywords: [
    "how to automate trim video",
    "automate video trimming",
    "automatically remove silence from video",
    "auto silence remover",
    "offline AI video trimmer",
    "remove dead air from video",
    "Windows silence remover",
    "Silero VAD video trimmer",
    "DeepFilterNet3 noise reduction",
    "Whisper VAD silence detection",
    "FFmpeg silence trimmer CLI",
    "cara potong bagian diam video otomatis",
    "hapus jeda hening video otomatis",
    "Mortem Trimmer",
  ],
  version: RELEASE_VERSION,
  platformLabel: "Windows x64",
  installerSizeLabel: "507 MB",
  licenseLabel: "MIT License",
  licenseUrl: `${GITHUB_URL}/blob/main/LICENSE`,
  authorName: "Fadhiilah Ahmad Zikri",
  authorUrl: "https://github.com/fadhiilahahmadzikri",
  repositoryUrl: GITHUB_URL,
  releasesUrl: `${GITHUB_URL}/releases/latest`,
  downloadUrl: `${GITHUB_URL}/releases/download/v${RELEASE_VERSION}/${INSTALLER_FILENAME}`,
  checksumUrl: `${GITHUB_URL}/releases/download/v${RELEASE_VERSION}/${INSTALLER_FILENAME}.sha256`,
  docsUrl: `${GITHUB_URL}#readme`,
  hero: {
    title: "Automate video silence trimming—100% offline by default",
    subtitle:
      "Remove dead air and background noise from any video automatically. Right-click in Windows Explorer or automate via CLI.",
    primaryCtaLabel: "Download for Windows",
  },
  navItems: [
    { label: "Features", href: "#capabilities" },
    { label: "FAQ", href: "#faq" },
    { label: "Setup", href: "#setup" },
    { label: "Releases", href: `${GITHUB_URL}/releases`, external: true },
  ] satisfies readonly NavItem[],
  pillars: [
    {
      id: "offline",
      title: "100% Offline AI Stack",
      description:
        "Silero VAD v6.2, Faster-Whisper, DeepFilterNet3, and FFmpeg run locally with zero cloud uploads or runtime downloads.",
    },
    {
      id: "explorer",
      title: "Explorer Right-Click Ready",
      description:
        "Right-click any video in Windows Explorer via Trim This Video, with a fast IPC daemon, tray progress popup, and PyQt6 tuner.",
    },
    {
      id: "verified",
      title: "Non-Destructive & Verified",
      description:
        "Keyframe-aligned parallel chunking, atomic temp writes, and PyAV stream checks preserve original files and AV sync.",
    },
  ] satisfies readonly FeaturePillar[],
  faq: [
    {
      id: "automate-trim",
      question: "How does Mortem Trimmer automate video silence trimming?",
      answer:
        "It analyzes speech activity using Silero VAD, Faster-Whisper, or Energy Gate, splits only at safe keyframes, removes silent gaps, optionally cleans background noise with DeepFilterNet3 or Spectral Gating, and verifies stream duration and AV sync with PyAV.",
    },
    {
      id: "explorer-workflow",
      question: "How do I trim videos directly from Windows Explorer?",
      answer:
        "After installing the Windows setup, right-click one or multiple media files (.mp4, .mkv, .mov, .webm, .wav, .mp3) and choose Trim This Video. A lightweight shim queues all selected files into a single background tray worker without opening extra windows.",
    },
    {
      id: "gpu-offline",
      question: "Does it require an internet connection or a dedicated GPU?",
      answer:
        "No. All AI models, PyTorch CPU runtime, and managed FFmpeg binaries are bundled offline inside the installer. Under the default G2 policy, hardware encoders (NVENC, QSV, AMF) accelerate rendering when available and automatically fall back to CPU.",
    },
    {
      id: "prebuilt-vs-custom",
      question:
        "Should I use the Prebuilt Windows Installer or Custom CLI / Source Setup?",
      answer:
        "Use the Prebuilt Windows Installer (.exe) if you want zero-configuration Explorer integration, tray daemon, and PyQt6 settings UI right away. Choose Custom CLI or Python source setup if you want scripted automation, headless batch pipelines, or custom silent install flags.",
    },
    {
      id: "safety-checksum",
      question: "Are my original videos modified, and how can I verify the download?",
      answer:
        "Original files are never overwritten; Mortem Trimmer writes atomically to a temporary file and outputs {name}.trimmed.{ext}. You can verify every release binary against its published .sha256 checksum on GitHub Releases.",
    },
  ] satisfies readonly FaqEntry[],
  customSetup: {
    prebuiltTitle: "Prebuilt Windows Installer",
    prebuiltDescription:
      "Ready-to-run per-user Inno Setup installer bundling Python, FFmpeg, Silero VAD v6.2, Faster-Whisper, DeepFilterNet3, and Explorer shell integration.",
    customTitle: "Custom CLI & Source Automation",
    customDescription:
      "Automate trimming in scripts, run silent installs without registering Explorer menus, or build directly from Python 3.11.5 source.",
    commands: [
      {
        id: "cli-trim",
        label: "Automate trim + DeepFilterNet3 denoise",
        command:
          "autosilenttrimmer-cli.exe -i raw.mp4 -o clean.mp4 --vad silero -m deepfilter",
      },
      {
        id: "silent-install",
        label: "Silent install without Explorer menu",
        command:
          '.\\MortemTrimmer-Setup-1.1.0-win-x64.exe /VERYSILENT /NORESTART /TASKS=none',
      },
      {
        id: "source-setup",
        label: "Run from Python 3.11.5 source",
        command:
          "git clone https://github.com/fadhiilahahmadzikri/mortemtrimmer.git && uv venv --python 3.11.5 .venv",
      },
    ] satisfies readonly CliCommandExample[],
  },
} as const;
