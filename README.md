# ManimGX 站点

ManimGX 是 TaopleOne 用 Manim 制作的一系列知识讲解动画。这个仓库是它的介绍站：

- `index.html` 首页
- `works.html` 作品：场景代码片段和动画视频并排
- `how.html` 怎么做的：场景、旁白与配音、导出
- `log.html` 更新记录

线上地址：https://goaltang.github.io/manimgx/ ，主站：https://goaltang.github.io/

## 构建

页面由 `tools/build.py` 生成，纯 HTML/CSS/JS，没有依赖。

```sh
python3 tools/build.py            # 用 src/snippets.json 生成页面
python3 tools/build.py --extract  # 先从素材目录（MANIMGX_SRC，默认 /mnt/d/ManimGX）重新截取代码
```

作品文字来自主站的 `data/works.json`（存了一份在 `src/works.json`）。视频和封面直接引用主站的
`films/<id>.mp4` 和 `covers/<id>.jpg`，仓库里不放视频。推送到 `main` 后由 `.github/workflows/pages.yml` 部署。
