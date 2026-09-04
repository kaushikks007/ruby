"""Ruby Avatar — Phase 6: 3D spider overlay (Three.js + Electron, always-on-top).

Hosted as an Electron transparent overlay window rendering ruby/avatar.html.
State ("idle" | "listening" | "speaking") is driven from Python via the local
AvatarStateServer; the renderer polls it and animates accordingly. All local.
"""
from ruby.avatar.bridge import AvatarStateServer, launch_electron, VALID_STATES

__all__ = ["AvatarStateServer", "launch_electron", "VALID_STATES"]
