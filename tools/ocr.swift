// Vision OCR over rendered pages, emitting the shape `tier_pages.py --ocr` expects:
// one JSON object per image, with `path` and `text`.
//
// This pass is looking for PRINTED text inside pasted screenshots, not handwriting.
// `tier_pages` only calls a page a screenshot when the OCR text is both much longer
// than the PDF's own text layer and mostly real dictionary words, and garbled
// handwriting fails that second test by construction. An engine that tried harder on
// handwriting would make this worse, not better, by inflating the length comparison.
//
// Usage: ocr <png> [<png>...]  > pages-ocr.jsonl

import CoreGraphics
import Foundation
import ImageIO
import Vision

struct Result: Codable {
    let path: String
    let text: String
    let error: String?
}

func ocr(_ path: String) -> Result {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        return Result(path: path, text: "", error: "unreadable")
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true

    do {
        try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    } catch {
        return Result(path: path, text: "", error: "\(error)")
    }

    // Top candidate per observation, in reading order. Vision returns one observation
    // per detected line, which is the granularity the validity score wants.
    let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    return Result(path: path, text: lines.joined(separator: "\n"), error: nil)
}

let paths = CommandLine.arguments.dropFirst()
if paths.isEmpty {
    FileHandle.standardError.write(
        "usage: ocr <png> [<png>...]  > pages-ocr.jsonl\n".data(using: .utf8)!)
    exit(1)
}

let encoder = JSONEncoder()
for path in paths {
    if let data = try? encoder.encode(ocr(path)),
       let line = String(data: data, encoding: .utf8) {
        print(line)
        fflush(stdout)
    }
}
