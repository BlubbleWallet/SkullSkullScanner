import aiohttp
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def fetch(session, url, headers=None):
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                return await resp.json()
    except:
        pass
    return None

async def scan_token(ca: str):
    try:
        async with aiohttp.ClientSession() as session:
            dex_task = fetch(session, f"https://api.dexscreener.com/latest/dex/tokens/{ca}")
            rugcheck_task = fetch(session, f"https://api.rugcheck.xyz/v1/tokens/{ca}/report")
            
            dex_data, rug_data = await asyncio.gather(dex_task, rugcheck_task)

            # Parse Dexscreener
            token_name = "Unknown"
            token_symbol = "???"
            mc = "N/A"
            liq = "N/A"
            liq_sol = "N/A"
            vol_1h = "N/A"
            vol_24h = "N/A"
            price_change_5m = "N/A"
            price_change_1h = "N/A"
            price_change_6h = "N/A"
            price_change_24h = "N/A"
            age = "N/A"

            if dex_data and dex_data.get("pairs"):
                pair = dex_data["pairs"][0]
                token_name = pair.get("baseToken", {}).get("name", "Unknown")
                token_symbol = pair.get("baseToken", {}).get("symbol", "???")
                
                mc_val = pair.get("marketCap") or pair.get("fdv", 0)
                mc = f"${mc_val:,.0f}" if mc_val else "N/A"
                
                liq_val = pair.get("liquidity", {}).get("usd", 0)
                liq_sol_val = pair.get("liquidity", {}).get("quote", 0)
                liq = f"${liq_val:,.0f}" if liq_val else "N/A"
                liq_sol = f"{liq_sol_val:,.0f} SOL" if liq_sol_val else "N/A"
                
                vol_1h_val = pair.get("volume", {}).get("h1", 0)
                vol_24h_val = pair.get("volume", {}).get("h24", 0)
                vol_1h = f"${vol_1h_val:,.0f}" if vol_1h_val else "N/A"
                vol_24h = f"${vol_24h_val:,.0f}" if vol_24h_val else "N/A"
                
                pc = pair.get("priceChange", {})
                def fmt_pc(v):
                    if v is None: return "N/A"
                    emoji = "🟢" if v >= 0 else "🔴"
                    return f"{'+' if v >= 0 else ''}{v:.1f}% {emoji}"
                
                price_change_5m = fmt_pc(pc.get("m5"))
                price_change_1h = fmt_pc(pc.get("h1"))
                price_change_6h = fmt_pc(pc.get("h6"))
                price_change_24h = fmt_pc(pc.get("h24"))
                
                created_at = pair.get("pairCreatedAt", 0)
                if created_at:
                    import time
                    age_sec = time.time() - (created_at / 1000)
                    if age_sec < 3600:
                        age = f"{int(age_sec/60)}m"
                    elif age_sec < 86400:
                        age = f"{int(age_sec/3600)}h"
                    elif age_sec < 2592000:
                        age = f"{int(age_sec/86400)}d"
                    else:
                        age = f"{int(age_sec/2592000)}mo"

            # Parse RugCheck
            mint_auth = False
            freeze_auth = False
            lp_burnt_pct = 0
            is_honeypot = False
            total_holders = 0
            top_holders = []
            risks = []
            top_10_pct = 0
            bundles = 0
            snipers = 0
            dev_hold_pct = 0
            top_holders_raw = []

            if rug_data:
                risks = rug_data.get("risks", [])
                
                for risk in risks:
                    name = risk.get("name", "").lower()
                    if "mint" in name:
                        mint_auth = True
                    if "freeze" in name:
                        freeze_auth = True
                    if "honeypot" in name or "not sellable" in name:
                        is_honeypot = True

                markets = rug_data.get("markets", [])
                if markets:
                    raw_lp = markets[0].get("lp", {}).get("lpBurnedPct", 0) or 0
                    # normalize: if value is 0-1 range, multiply by 100
                    lp_burnt_pct = round(raw_lp * 100, 1) if raw_lp <= 1 else round(raw_lp, 1)
                
                top_holders_raw = rug_data.get("topHolders", [])
                total_holders = rug_data.get("totalHolderCount", 0)
                
                if top_holders_raw:
                    for i, h in enumerate(top_holders_raw[:10]):
                        addr = h.get("address", "???")
                        raw_pct = h.get("pct", 0)
                        pct = raw_pct * 100 if raw_pct <= 1 else raw_pct
                        is_insider = h.get("insider", False)
                        short_addr = f"{addr[:4]}...{addr[-4:]}" if len(addr) > 8 else addr
                        
                        if pct >= 10:
                            emoji = "🔥"
                        elif pct >= 5:
                            emoji = "🐋"
                        elif pct >= 2:
                            emoji = "🐬"
                        else:
                            emoji = "👤"
                        
                        insider_tag = " ⚠️" if is_insider else ""
                        top_holders.append(f"#{i+1} `{short_addr}` [{pct:.1f}%] {emoji}{insider_tag}")
                    
                    top_10_pct = sum(
                        (h.get("pct", 0) * 100 if h.get("pct", 0) <= 1 else h.get("pct", 0))
                        for h in top_holders_raw[:10]
                    )
                
                # Dev holdings
                creator_tokens = rug_data.get("creatorTokens", [])
                for t in creator_tokens:
                    if t.get("mint") == ca:
                        raw_dev = t.get("pct", 0)
                        dev_hold_pct = raw_dev * 100 if raw_dev <= 1 else raw_dev
                
                for risk in risks:
                    if "bundle" in risk.get("name", "").lower():
                        bundles = risk.get("value", 1)
                    if "sniper" in risk.get("name", "").lower():
                        snipers = risk.get("value", 1)

            # Safety Score
            score = 10
            red_flags = []
            warnings = []

            if is_honeypot:
                score -= 4
                red_flags.append("🔴 HONEYPOT — Token cannot be sold!")
            if mint_auth:
                score -= 2
                red_flags.append("🔴 Mint ON → Dev can mint new tokens")
            if freeze_auth:
                score -= 2
                red_flags.append("🔴 Freeze ON → Dev can freeze wallets")
            if lp_burnt_pct < 50:
                score -= 2
                red_flags.append(f"🔴 LP Burnt {lp_burnt_pct}% → Rug pull risk")
            if top_10_pct > 50:
                score -= 1
                red_flags.append(f"🔴 Top 10 hold {top_10_pct:.1f}% of supply")
            elif top_holders_raw:
                top1_raw = top_holders_raw[0].get("pct", 0)
                top1_pct = top1_raw * 100 if top1_raw <= 1 else top1_raw
                if top1_pct > 15:
                    score -= 1
                    warnings.append(f"⚠️ Top holder > 15% — WHALE ALERT")
            if bundles > 0:
                score -= 1
                red_flags.append(f"🔴 Bundle detected ({bundles})")
            if snipers > 0:
                score -= 1
                warnings.append(f"⚠️ Snipers detected ({snipers})")

            score = max(0, score)

            if score >= 8:
                score_emoji = "🟢"
                score_label = "SAFE"
            elif score >= 5:
                score_emoji = "🟡"
                score_label = "MODERATE"
            elif score >= 3:
                score_emoji = "🟠"
                score_label = "RISKY"
            else:
                score_emoji = "🔴"
                score_label = "HIGH RISK"

            mint_str = "🔴 ON" if mint_auth else "🟢 OFF"
            freeze_str = "🔴 ON" if freeze_auth else "🟢 OFF"
            lp_str = f"{'🟢' if lp_burnt_pct >= 80 else '🟡' if lp_burnt_pct >= 50 else '🔴'} {lp_burnt_pct}% Burnt"
            honeypot_str = "🔴 HONEYPOT!" if is_honeypot else "🟢 SAFE (Sellable)"
            holders_text = "\n".join(top_holders) if top_holders else "No data available"

            flags_text = ""
            if red_flags or warnings:
                all_flags = red_flags + warnings
                flags_text = f"\n\n━━━━━━━━━━━━━━━━━━━━\n🚨 *RED FLAGS ({len(red_flags)} found)*\n━━━━━━━━━━━━━━━━━━━━\n"
                flags_text += "\n".join(all_flags)
            else:
                flags_text = "\n\n✅ *No red flags detected!*"

            msg = f"""💀 *{token_name} • ${token_symbol}*
`{ca}`

━━━━━━━━━━━━━━━━━━━━
🛡️ *SAFETY SCORE: {score}/10 {score_emoji} {score_label}*
━━━━━━━━━━━━━━━━━━━━

🪙 Mint: {mint_str}  |  ❄️ Freeze: {freeze_str}
🔥 LP: {lp_str}
🍯 Honeypot: {honeypot_str}

━━━━━━━━━━━━━━━━━━━━
📊 *MARKET INFO*
━━━━━━━━━━━━━━━━━━━━
⏰ Age: {age}
💰 MC: {mc}
💧 Liq: {liq} [{liq_sol}]
📊 Vol 1h: {vol_1h}  |  24h: {vol_24h}

📉 *PRICE CHANGE*
├ 5m:  {price_change_5m}
├ 1h:  {price_change_1h}
├ 6h:  {price_change_6h}
└ 24h: {price_change_24h}

━━━━━━━━━━━━━━━━━━━━
👥 *HOLDERS & WALLETS*
━━━━━━━━━━━━━━━━━━━━
👤 Total Holders: {total_holders:,}
📦 Top 10 Hold: {top_10_pct:.1f}%

🏆 *TOP 10 WALLETS*
{holders_text}

━━━━━━━━━━━━━━━━━━━━
🧑‍💻 *DEV & BUNDLE*
━━━━━━━━━━━━━━━━━━━━
👨‍💻 Dev Hold: {dev_hold_pct:.1f}%
📦 Bundles: {'✅ 0' if bundles == 0 else f'⚠️ {bundles}'}
🎯 Snipers: {'✅ None' if snipers == 0 else f'⚠️ {snipers}'}{flags_text}
━━━━━━━━━━━━━━━━━━━━"""

            keyboard = [
                [
                    InlineKeyboardButton("📈 Chart", url=f"https://dexscreener.com/solana/{ca}"),
                    InlineKeyboardButton("🔎 Solscan", url=f"https://solscan.io/token/{ca}"),
                    InlineKeyboardButton("🐦 Birdeye", url=f"https://birdeye.so/token/{ca}"),
                ],
                [
                    InlineKeyboardButton("🔁 Refresh", callback_data=f"refresh_{ca}"),
                    InlineKeyboardButton("💀 RugCheck", url=f"https://rugcheck.xyz/tokens/{ca}"),
                ]
            ]
            return msg, InlineKeyboardMarkup(keyboard)

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔁 Try Again", callback_data=f"refresh_{ca}")]]
        return f"❌ *Failed to scan token!*\n\n`{ca}`\n\nAPI timeout or token not found. Please try again!", InlineKeyboardMarkup(keyboard)
