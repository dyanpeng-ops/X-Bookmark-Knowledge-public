// 本地 OCR（macOS Vision 框架）— 零安装、零 API 花费、数据不出本机。
//
// 用途：为 Markdown 里的配图提取**文字**（截图类图片），供图片 caption 的"可检索描述"。
// 由 `src/media/vision_ocr.py` 调用；首次使用时编译到 `data/state/bin/`（gitignored）。
//
// 用法：  vision_ocr <图片路径>
// 输出：  {"lines": ["第一行", ...], "count": N, "langs": ["zh-Hans", ...]}   ← stdout（JSON）
// 退出码：0 成功；2 图片读取失败；3 OCR 失败
//
// 说明：本文件**只读**图片、不联网、不写盘（除系统日志外无副作用）。

import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count > 1 else {
    FileHandle.standardError.write("usage: vision_ocr <image-path>\n".data(using: .utf8)!)
    exit(64)
}
let path = args[1]
guard let image = NSImage(contentsOfFile: path),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("image load failed: \(path)\n".data(using: .utf8)!)
    exit(2)
}

// 语言顺序：中文优先（本项目书签以中文为主），再英文兜底。
let languages = ["zh-Hans", "zh-Hant", "en-US"]

var recognized: [String] = []
let request = VNRecognizeTextRequest { req, _ in
    guard let observations = req.results as? [VNRecognizedTextObservation] else { return }
    for observation in observations {
        if let candidate = observation.topCandidates(1).first {
            let text = candidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
            if !text.isEmpty { recognized.append(text) }
        }
    }
}
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = languages

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write("ocr failed: \(error)\n".data(using: .utf8)!)
    exit(3)
}

let payload: [String: Any] = ["lines": recognized, "count": recognized.count, "langs": languages]
do {
    let data = try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
} catch {
    FileHandle.standardError.write("json encode failed\n".data(using: .utf8)!)
    exit(3)
}
