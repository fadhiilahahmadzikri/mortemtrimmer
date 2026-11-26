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

const GITHUB_URL = "https://github.com/fadhiilahahmadzikri/mortemtrimmer";
const RELEASE_VERSION = "1.1.0";
const INSTALLER_FILENAME = `MortemTrimmer-Setup-${RELEASE_VERSION}-win-x64.exe`;

export const SITE_CONFIG = {
  name: "Mortem Trimmer",
  wordmark: "MORTEM TRIMMER",
  tagline: "Self-Contained Offline AI Silence Remover & Noise Reduction Production Suite",
  version: RELEASE_VERSION,
  platformLabel: "Windows x64",
  installerSizeLabel: "507 MB",
  licenseLabel: "MIT License",
  authorName: "Fadhiilah Ahmad Zikri",
  authorUrl: "https://github.com/fadhiilahahmadzikri",
  repositoryUrl: GITHUB_URL,
  releasesUrl: `${GITHUB_URL}/releases/latest`,
  downloadUrl: `${GITHUB_URL}/releases/download/v${RELEASE_VERSION}/${INSTALLER_FILENAME}`,
  checksumUrl: `${GITHUB_URL}/releases/download/v${RELEASE_VERSION}/${INSTALLER_FILENAME}.sha256`,
  docsUrl: `${GITHUB_URL}#readme`,
  hero: {
    title: "Cut dead air from every video—100% offline by default",
    subtitle:
      "Self-contained AI silence removal and DeepFilterNet3 noise reduction. Right-click any video in Explorer or automate via CLI.",
    primaryCtaLabel: "Download for Windows",
    secondaryCtaLabel: "Release Notes",
  },
  navItems: [
    { label: "Features", href: "#capabilities" },
    { label: "Releases", href: `${GITHUB_URL}/releases`, external: true },
    { label: "Docs", href: `${GITHUB_URL}#cheat-sheet`, external: true },
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
} as const;
