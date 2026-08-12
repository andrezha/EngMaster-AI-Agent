from __future__ import annotations

import argparse
import hashlib
import html
import shutil
import sys
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _technical_guide_html(exe_name: str, sha256: str) -> str:
    safe_name = html.escape(exe_name)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>英思成 运行前必读</title>
<style>
body {{ margin:0; background:#f4f7fb; color:#1f2937; font-family:"Microsoft YaHei","Segoe UI",sans-serif; line-height:1.75; }}
main {{ max-width:900px; margin:32px auto; padding:0 20px 50px; }}
.hero,.card {{ background:white; border:1px solid #dbe3ef; border-radius:16px; padding:24px 28px; margin-bottom:18px; box-shadow:0 5px 20px rgba(15,23,42,.06); }}
.hero {{ border-top:6px solid #2563eb; }}
h1 {{ margin:0 0 8px; color:#123b72; font-size:28px; }}
h2 {{ color:#174f91; font-size:20px; margin:0 0 10px; }}
.safe {{ background:#ecfdf5; border-color:#86efac; }}
.warn {{ background:#fffbeb; border-color:#fcd34d; }}
.stop {{ background:#fef2f2; border-color:#fca5a5; }}
code {{ background:#eef2ff; padding:2px 6px; border-radius:5px; word-break:break-all; }}
.hash {{ display:block; padding:12px; margin-top:8px; background:#0f172a; color:#d1fae5; border-radius:8px; font-family:Consolas,monospace; word-break:break-all; }}
li {{ margin:7px 0; }}
a {{ color:#1d4ed8; }}
</style>
</head>
<body><main>
<section class="hero">
<h1>英思成 运行前必读</h1>
<p>本版本是免安装的 Windows 单文件程序，目前未购买数字签名证书。因此 Windows 或第三方杀毒软件可能显示“未知发布者”、SmartScreen 提醒或误报。请先完成下面的安全核对，再决定是否运行。</p>
</section>

<section class="card safe">
<h2>第一步：先确认文件来源和校验值</h2>
<ol>
<li>只使用官方购买页面提供的压缩包，不运行群聊转发、网盘二次分享或陌生邮件附件。</li>
<li>确认程序文件名为 <code>{safe_name}</code>。</li>
<li>当前正式文件 SHA-256：</li>
</ol>
<span class="hash">{sha256}</span>
<p>核对方法：在程序所在文件夹空白处按住 Shift 并右键打开 PowerShell，执行：</p>
<span class="hash">Get-FileHash -Algorithm SHA256 ".\{safe_name}"</span>
<p>结果必须与上面的 64 位字符完全一致。只要不一致，就不要运行，请重新从官方来源下载。</p>
</section>

<section class="card">
<h2>第二步：先完整解压，再运行</h2>
<ol>
<li>右键下载的 ZIP，选择“全部解压缩”。</li>
<li>不要直接在压缩包预览窗口中运行 EXE。</li>
</ol>
</section>

<section class="card warn">
<h2>第三步：出现 Windows SmartScreen 提醒</h2>
<p>如果窗口显示“Windows 已保护你的电脑”或“无法识别的应用”：</p>
<ol>
<li>再次确认文件名和 SHA-256。</li>
<li>确认无误后点击“更多信息”，核对应用名称，再选择“仍要运行”。</li>
<li>如果没有“更多信息/仍要运行”，请查看是否为 Smart App Control（智能应用控制）或单位设备管理策略拦截。</li>
</ol>
<p>解压后双击软件，如果软件没有打开，同时 Windows 弹出“智能应用控制已阻止此应用”“智能应用控制已阻止可能不安全的应用”或类似提示，并且没有“更多信息”或“仍要运行”选项，说明本次运行被智能应用控制阻止。</p>
<p>用户可以自行选择：</p>
<ul>
<li>自行关闭“智能应用控制”后运行（安装）。</li>
<li>不修改系统设置，暂不在这台电脑上运行（不安装）。</li>
</ul>
<p><strong>关闭路径通常为：</strong><br>Windows 安全中心 → 应用和浏览器控制 → 智能应用控制设置 → 关闭</p>
<p><strong>请注意：</strong>智能应用控制与杀毒软件实时防护不是同一个功能。无需关闭 Microsoft Defender、第三方杀毒软件或防火墙。</p>
</section>

<section class="card warn">
<h2>第四步：Windows Defender 提示或隔离</h2>
<ol>
<li>打开“Windows 安全中心” → “病毒和威胁防护” → “保护历史记录”。</li>
<li>找到与本程序文件名和下载时间完全对应的记录，先查看检测名称和受影响文件。</li>
<li>只有在来源可信且 SHA-256 完全一致时，才可对这个文件选择“允许在设备上”或“还原”；若文件已经被移除，允许后需要重新下载。</li>
<li>若检测级别高、文件名不一致、校验失败或无法判断，请保持隔离，不要继续运行。</li>
</ol>
</section>

<section class="card">
<h2>第五步：其他杀毒软件提示</h2>
<p>360、火绒、腾讯电脑管家及其他安全软件的按钮名称不同。通用原则是：</p>
<ul>
<li>先查看隔离区、查杀历史或安全日志，确认拦截对象确实是本 EXE。</li>
<li>核对官方来源和 SHA-256 后，只还原或信任这个具体文件。</li>
<li>仍有疑问时，请保持隔离，并参考购买页面、随程序提供的说明或安全软件厂商的官方操作指引。</li>
</ul>
</section>

<section class="card">
<h2>官方安全参考</h2>
<ul>
<li><a href="https://support.microsoft.com/en-us/windows/security/information-about-the-attachment-manager-in-microsoft-windows">Microsoft：检查和解除下载文件阻止</a></li>
<li><a href="https://support.microsoft.com/en-us/windows/security/windows-security/protection-history-in-the-windows-security-app">Microsoft：Windows 安全中心保护历史记录</a></li>
<li><a href="https://www.microsoft.com/wdsi/filesubmission">Microsoft：提交误报文件进行分析</a></li>
</ul>
</section>
</main></body></html>"""


def guide_html(exe_name: str, sha256: str) -> str:
    safe_name = html.escape(exe_name)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>英思成 运行前必读</title>
<style>
body {{ margin:0; background:#f4f7fb; color:#253247; font-family:"Microsoft YaHei","Segoe UI",sans-serif; line-height:1.8; }}
main {{ max-width:780px; margin:30px auto; padding:0 18px 48px; }}
.card {{ background:white; border:1px solid #dce5f1; border-radius:18px; padding:26px 30px; margin-bottom:18px; box-shadow:0 6px 22px rgba(30,58,95,.07); }}
.hero {{ border-top:7px solid #2563eb; }}
.step {{ display:flex; gap:18px; align-items:flex-start; }}
.number {{ flex:0 0 42px; height:42px; border-radius:50%; background:#2563eb; color:white; font-size:22px; font-weight:bold; text-align:center; line-height:42px; }}
h1 {{ margin:0 0 8px; color:#173f73; font-size:29px; }}
h2 {{ margin:2px 0 8px; color:#174f91; font-size:21px; }}
.tip {{ background:#eff6ff; border-color:#93c5fd; }}
.warn {{ background:#fff8e8; border-color:#f5c451; }}
.stop {{ background:#fff1f2; border-color:#fda4af; }}
.button {{ display:inline-block; padding:3px 10px; background:#e5e7eb; border:1px solid #cbd5e1; border-radius:7px; font-weight:bold; color:#111827; }}
.small {{ color:#64748b; font-size:14px; }}
</style>
</head>
<body><main>
<section class="card hero">
<h1>英思成 运行前必读</h1>
<p>本软件暂时没有数字签名，所以第一次打开时，Windows 或杀毒软件可能弹出提醒。这不代表软件一定有病毒，请按照下面三步操作。</p>
</section>

<section class="card step">
<div class="number">1</div><div>
<h2>先解压</h2>
<p>右键下载的压缩包，选择 <span class="button">全部解压缩</span>。解压完成后，再打开新文件夹。</p>
<p class="small">不要直接在压缩包里面双击程序。</p>
</div></section>

<section class="card step">
<div class="number">2</div><div>
<h2>双击程序</h2>
<p>双击 <strong>{safe_name}</strong>。</p>
</div></section>

<section class="card step">
<div class="number">3</div><div>
<h2>出现 Windows 蓝色提醒时</h2>
<p>如果看到“Windows 已保护你的电脑”：</p>
<p>先点击 <span class="button">更多信息</span>，再点击 <span class="button">仍要运行</span>。</p>
</div></section>

<section class="card warn">
<h2>如果“智能应用控制”阻止运行</h2>
<p>解压后双击软件，如果软件没有打开，同时 Windows 弹出“智能应用控制已阻止此应用”“智能应用控制已阻止可能不安全的应用”或类似提示，并且没有“更多信息”或“仍要运行”选项，说明本次运行被智能应用控制阻止。</p>
<p>用户可以自行选择：</p>
<ul>
<li>自行关闭“智能应用控制”后运行（安装）。</li>
<li>不修改系统设置，暂不在这台电脑上运行（不安装）。</li>
</ul>
<p><strong>关闭路径通常为：</strong><br>Windows 安全中心 → 应用和浏览器控制 → 智能应用控制设置 → 关闭</p>
<p><strong>请注意：</strong>智能应用控制与杀毒软件实时防护不是同一个功能。无需关闭 Microsoft Defender、第三方杀毒软件或防火墙。</p>
</section>

<section class="card warn">
<h2>如果杀毒软件拦截了怎么办？</h2>
<p><strong>不要关闭杀毒软件，也不要随便修改电脑设置。</strong></p>
<p>请参考所使用安全软件的官方管理方法，仅对本软件文件执行允许、信任或恢复操作；不熟悉电脑操作的用户，可以请熟悉计算机操作的人士协助处理。</p>
</section>

<p class="small">文件校验信息已经随压缩包保存，可用于自行核对文件是否完整。SHA-256：{sha256}</p>
</main></body></html>"""


def build_package(exe: Path, output_dir: Path) -> tuple[Path, Path]:
    exe = exe.resolve(strict=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    copied_exe = output_dir / exe.name
    shutil.copy2(exe, copied_exe)
    digest = sha256_file(copied_exe)

    guide = output_dir / "00_运行前必读_未签名程序安全说明.html"
    guide.write_text(guide_html(copied_exe.name, digest), encoding="utf-8")
    old_customer_checksum = output_dir / "01_客服核验文件_普通用户无需打开.txt"
    old_customer_checksum.unlink(missing_ok=True)
    checksum = output_dir / "01_文件校验值_SHA256.txt"
    checksum.write_text(
        "本文件用于自行核对程序文件是否完整。\n"
        "核对步骤请参考随程序提供的《运行前必读》说明。\n\n"
        f"SHA-256: {digest}\n文件名: {copied_exe.name}\n",
        encoding="utf-8",
    )

    zip_path = output_dir.parent / f"{output_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.iterdir()):
            archive.write(path, arcname=f"{output_dir.name}/{path.name}")
    return output_dir, zip_path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Build the safe customer delivery ZIP.")
    parser.add_argument("exe", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    output_dir, zip_path = build_package(args.exe, args.output_dir)
    print(output_dir)
    print(zip_path)


if __name__ == "__main__":
    main()
