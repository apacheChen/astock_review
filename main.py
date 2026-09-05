"""astock_review 主入口
Kivy 界面:候选榜 / 自选股 / 复盘历史 三个页签
复盘在后台线程执行,完成后自动落库并刷新;启动时恢复最近一次结果"""
import threading
import time as _time
import traceback
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.utils import platform
from loguru import logger

try:
    from src.datasource import em_client
    from src.pipeline.funnel import run_funnel
    from src.strategy.scoring import rank
    from src.storage import dao
except ImportError:
    from datasource import em_client
    from pipeline.funnel import run_funnel
    from strategy.scoring import rank
    from storage import dao

# PC 上模拟手机竖屏预览
if platform not in ("android", "ios"):
    Window.size = (400, 780)

# ===== 中文字体补丁:安卓上改用系统自带中文字体 =====
from kivy.core.text import LabelBase
if platform == "android":
    for _f in ("/system/fonts/NotoSansCJK-Regular.ttc",
               "/system/fonts/DroidSansFallback.ttf",
               "/system/fonts/NotoSansSC-Regular.otf"):
        if Path(_f).exists():
            LabelBase.register(name="Roboto", fn_regular=_f)
            break


RED = "#e63946"    # 涨(A股习惯红涨)
GREEN = "#2a9d8f"  # 跌
ORANGE = "#f4a261"
GREY = "#8d99ae"

try:
    _d = Path.cwd() / "data"
    _d.mkdir(exist_ok=True)
    logger.add(str(_d / "app.log"), rotation="5 MB",
               encoding="utf-8", level="INFO")
except Exception:
    pass


def _pct_color(p):
    try:
        return RED if float(p) >= 0 else GREEN
    except Exception:
        return GREY


def _fmt_price(p):
    try:
        return f"{float(p):.2f}"
    except Exception:
        return "—"


def _fmt_pct(p):
    try:
        return f"{float(p):+.2f}%"
    except Exception:
        return "—"


def _stars(n):
    n = max(0, min(5, int(n or 0)))
    return "★" * n + "☆" * (5 - n)


class RowButton(Button):
    """列表中的一行(可点击,双行文本)"""
    def __init__(self, text, on_tap, **kw):
        super().__init__(**kw)
        self.text = text
        self.markup = True
        self.halign = "left"
        self.valign = "middle"
        self.size_hint_y = None
        self.height = dp(62)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (1, 1, 1, 0.07)
        self.padding = [dp(10), dp(4)]
        self.bind(width=lambda inst, w:
                  setattr(inst, "text_size", (w - dp(16), None)))
        self.bind(on_press=lambda inst: on_tap())


class ReviewApp(App):
    title = "A股复盘助手"

    # ---------- 界面骨架 ----------
    def build(self):
        self._running = False
        self.tabs = TabbedPanel(do_default_tab=False, tab_height=dp(44))
        self.tab_cand = TabbedPanelItem(text="候选榜")
        self.tab_watch = TabbedPanelItem(text="自选股")
        self.tab_hist = TabbedPanelItem(text="历史")
        self.tabs.add_widget(self.tab_cand)
        self.tabs.add_widget(self.tab_watch)
        self.tabs.add_widget(self.tab_hist)

        self._build_cand_tab()
        self._build_watch_tab()
        self._build_hist_tab()
        self.tabs.switch_to(self.tab_cand)

        Clock.schedule_once(lambda dt: (self.refresh_watch(),
                                        self.refresh_hist()), 0.3)
        Clock.schedule_once(self._restore_latest, 0.6)
        return self.tabs

    def _build_cand_tab(self):
        root = BoxLayout(orientation="vertical",
                         padding=dp(6), spacing=dp(6))
        top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        self.lbl_status = Label(text="点右侧按钮开始第一次复盘",
                                halign="left", valign="middle",
                                color=(0.85, 0.85, 0.85, 1))
        self.lbl_status.bind(width=lambda inst, w:
                             setattr(inst, "text_size", (w, None)))
        self.btn_run = Button(text="开始复盘", bold=True,
                              size_hint_x=None, width=dp(110),
                              background_normal="",
                              background_color=(0.27, 0.48, 0.72, 1))
        self.btn_run.bind(on_press=lambda inst: self.start_review())
        top.add_widget(self.lbl_status)
        top.add_widget(self.btn_run)
        root.add_widget(top)

        self.sv_cand = ScrollView()
        self.grid_cand = GridLayout(cols=1, size_hint_y=None,
                                    spacing=dp(4), padding=[0, dp(2)])
        self.grid_cand.bind(minimum_height=self.grid_cand.setter("height"))
        self.sv_cand.add_widget(self.grid_cand)
        root.add_widget(self.sv_cand)
        self.tab_cand.add_widget(root)

    def _build_watch_tab(self):
        root = BoxLayout(orientation="vertical",
                         padding=dp(6), spacing=dp(6))
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        tip = Label(text="点行可看详情/移除", halign="left",
                    color=(0.7, 0.7, 0.7, 1))
        tip.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        btn = Button(text="刷新", size_hint_x=None, width=dp(90))
        btn.bind(on_press=lambda inst: self.refresh_watch())
        top.add_widget(tip)
        top.add_widget(btn)
        root.add_widget(top)

        self.sv_watch = ScrollView()
        self.grid_watch = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        self.grid_watch.bind(minimum_height=self.grid_watch.setter("height"))
        self.sv_watch.add_widget(self.grid_watch)
        root.add_widget(self.sv_watch)
        self.tab_watch.add_widget(root)

    def _build_hist_tab(self):
        root = BoxLayout(orientation="vertical",
                         padding=dp(6), spacing=dp(6))
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        tip = Label(text="点某次记录可回看该次候选榜", halign="left",
                    color=(0.7, 0.7, 0.7, 1))
        tip.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        btn = Button(text="刷新", size_hint_x=None, width=dp(90))
        btn.bind(on_press=lambda inst: self.refresh_hist())
        top.add_widget(tip)
        top.add_widget(btn)
        root.add_widget(top)

        self.sv_hist = ScrollView()
        self.grid_hist = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        self.grid_hist.bind(minimum_height=self.grid_hist.setter("height"))
        self.sv_hist.add_widget(self.grid_hist)
        root.add_widget(self.sv_hist)
        self.tab_hist.add_widget(root)

    # ---------- 文本行 ----------
    def _row_text(self, r):
        pc = _pct_color(r.get("pct_chg"))
        tags = (str(r.get("tags") or "")).replace("|", " | ")
        line1 = (f"[b]{r.get('name') or ''}[/b] {r.get('symbol')}   "
                 f"[color={pc}][b]{_fmt_price(r.get('price'))} "
                 f"{_fmt_pct(r.get('pct_chg'))}[/b][/color]   "
                 f"[color={ORANGE}][b]{r.get('score')}分[/b][/color] "
                 f"{_stars(r.get('stars'))}")
        return line1 + "\n" + (tags if tags else "—")

    def _fill_candidates(self, records):
        self.grid_cand.clear_widgets()
        if not records:
            self.grid_cand.add_widget(
                Label(text="暂无候选", color=(0.6, 0.6, 0.6, 1)))
            return
        for r in records:
            self.grid_cand.add_widget(
                RowButton(self._row_text(r),
                          on_tap=lambda rr=r: self.show_detail(rr)))

    # ---------- 状态栏(线程安全) ----------
    def set_status(self, msg):
        Clock.schedule_once(lambda dt: self._set_status(msg))

    def _set_status(self, msg):
        self.lbl_status.text = msg

    # ---------- 启动恢复 ----------
    def _restore_latest(self, dt=None):
        try:
            df = dao.load_latest_results()
            if df is not None and not df.empty:
                self._fill_candidates(df.to_dict("records"))
                self.set_status(
                    f"已载入最近一次结果({len(df)}只),点「开始复盘」刷新")
            else:
                self.set_status("暂无历史结果,点「开始复盘」跑第一次")
        except Exception as e:
            logger.warning(f"恢复历史失败: {e}")

    # ---------- 复盘主流程 ----------
    def start_review(self):
        if self._running:
            return
        self._running = True
        self.btn_run.disabled = True
        self._t0 = _time.time()
        self._tick = Clock.schedule_interval(self._update_elapsed, 1)
        self.set_status("复盘中:快照→三层漏斗→打分,约3~6分钟…")
        threading.Thread(target=self._review_worker, daemon=True).start()

    def _update_elapsed(self, dt):
        self._set_status(
            f"复盘中…已用时 {int(_time.time() - self._t0)} 秒,请保持网络畅通")

    def _review_worker(self):
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            self.set_status("① 拉取全市场快照…")
            snapshot = em_client.fetch_market_snapshot()
            if snapshot is None or snapshot.empty:
                raise RuntimeError("快照为空,请检查网络后重试")
            n_snap = len(snapshot)

            self.set_status(f"② 快照{n_snap}只,三层漏斗筛选中…")
            final = run_funnel(snapshot)
            if final is None or final.empty:
                raise RuntimeError("漏斗结果为空(极端行情或网络波动)")

            self.set_status("③ 五维打分排序…")
            ranked = rank(final)
            dao.save_review_results(run_id, ranked)
            dao.save_run(run_id, n_snapshot=n_snap, n_final=len(ranked),
                         elapsed=round(_time.time() - self._t0, 1))
            Clock.schedule_once(
                lambda dt: self._on_review_done(ranked, run_id))
        except Exception as e:
            logger.error(traceback.format_exc())
            dao.save_run(run_id, status="error", error=str(e)[:200],
                         elapsed=round(_time.time() - self._t0, 1))
            msg = str(e)
            Clock.schedule_once(lambda dt: self._on_review_fail(msg))

    def _on_review_done(self, ranked, run_id):
        self._running = False
        self.btn_run.disabled = False
        if getattr(self, "_tick", None):
            self._tick.cancel()
        self.set_status(
            f"✅ 完成:{len(ranked)}只候选已保存,点行看详情")
        self._fill_candidates(ranked.to_dict("records"))
        self.refresh_hist()

    def _on_review_fail(self, msg):
        self._running = False
        self.btn_run.disabled = False
        if getattr(self, "_tick", None):
            self._tick.cancel()
        self.set_status(f"❌ 失败:{msg}(可重试)")

    # ---------- 详情弹窗 ----------
    def show_detail(self, r):
        sym = str(r.get("symbol") or "")
        name = r.get("name") or sym
        pc = _pct_color(r.get("pct_chg"))
        tags = (str(r.get("tags") or "")).replace("|", " | ")
        reasons = r.get("reasons") or "—"
        hist = dao.symbol_history(sym, limit=8)
        hist_lines = []
        if hist is not None and not hist.empty:
            for _, h in hist.iterrows():
                hist_lines.append(
                    f"  {h.get('run_time', '')}  "
                    f"{h.get('score')}分 {_stars(h.get('stars'))}")
        hist_text = ("复盘轨迹:\n" + "\n".join(hist_lines[:8])
                     if hist_lines else "复盘轨迹: 暂无")
        lines = [
            f"现价 {_fmt_price(r.get('price'))}  "
            f"[color={pc}]{_fmt_pct(r.get('pct_chg'))}[/color]",
            f"[color={ORANGE}][b]{r.get('score')}分[/b][/color] "
            f"{_stars(r.get('stars'))}",
            f"标签: {tags or '—'}",
            f"入选理由: {reasons}",
            "", hist_text,
        ]
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        lbl = Label(markup=True, text="\n".join(lines),
                    halign="left", valign="top")
        lbl.bind(width=lambda inst, w:
                 setattr(inst, "text_size", (w, None)))
        box.add_widget(lbl)

        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_watch = Button(
            text="移除自选" if dao.is_watched(sym) else "加入自选")

        def _toggle(inst):
            if dao.is_watched(sym):
                dao.remove_watch(sym)
                btn_watch.text = "加入自选"
            else:
                dao.add_watch(sym, str(name))
                btn_watch.text = "移除自选"
            self.refresh_watch()
        btn_watch.bind(on_press=_toggle)

        btn_close = Button(text="关闭")
        holder = {}
        btn_close.bind(on_press=lambda inst: holder["p"].dismiss())
        btns.add_widget(btn_watch)
        btns.add_widget(btn_close)
        box.add_widget(btns)

        popup = Popup(title=f"{name} {sym}", content=box,
                      size_hint=(0.92, 0.85))
        holder["p"] = popup
        popup.open()

    # ---------- 自选 ----------
    def refresh_watch(self, *a):
        self.grid_watch.clear_widgets()
        df = dao.list_watch()
        if df is None or df.empty:
            self.grid_watch.add_widget(
                Label(text="自选为空:在候选详情里点「加入自选」",
                      color=(0.6, 0.6, 0.6, 1)))
            return
        for _, r in df.iterrows():
            txt = (f"[b]{r.get('name') or ''}[/b] {r.get('symbol')}\n"
                   f"{r.get('note') or ''} 加入于 {r.get('added_time', '')}")
            self.grid_watch.add_widget(
                RowButton(txt,
                          on_tap=lambda rr=r.to_dict(): self.show_detail(rr)))

    # ---------- 历史 ----------
    def refresh_hist(self, *a):
        self.grid_hist.clear_widgets()
        runs = dao.list_runs()
        if runs is None or runs.empty:
            self.grid_hist.add_widget(
                Label(text="暂无复盘记录", color=(0.6, 0.6, 0.6, 1)))
            return
        for _, r in runs.iterrows():
            status = r.get("status") or "ok"
            icon = "✅" if status == "ok" else "❌"
            n_final = int(r.get("n_final") or 0)
            elapsed = r.get("elapsed")
            elapsed_s = f"{float(elapsed):.0f}s" if elapsed else "-"
            txt = (f"{icon} {r.get('run_time', '')}\n"
                   f"候选 {n_final} 只 · 用时 {elapsed_s}"
                   + (f" · {r.get('error')}" if status != "ok" else ""))
            rid = str(r.get("run_id"))
            self.grid_hist.add_widget(
                RowButton(txt, on_tap=lambda x=rid: self.show_run(x)))

    def show_run(self, run_id):
        df = dao.get_run_results(run_id)
        records = df.to_dict("records") if df is not None else []
        self._fill_candidates(records)
        self.tabs.switch_to(self.tab_cand)
        self.set_status(f"已载入 {run_id} 的结果({len(records)}只)")


if __name__ == "__main__":
    ReviewApp().run()
