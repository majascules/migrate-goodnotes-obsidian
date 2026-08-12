// Per-page text dump via PDFKit. Deliberately NO OCR fallback: the question this
// answers is whether a text layer exists in the file, so a page that renders as
// pure image must report zero characters rather than quietly being recognised.
// Usage: pdfpages <pdf> [<pdf>...]  → one JSON object per PDF on stdout.

import Foundation
import PDFKit

struct Page: Codable {
    let page: Int
    let chars: Int
    let text: String
}

struct Doc: Codable {
    let path: String
    let pageCount: Int
    let totalChars: Int
    let pagesWithText: Int
    let pages: [Page]
    let error: String?
}

let encoder = JSONEncoder()

func dump(_ path: String) -> Doc {
    guard let doc = PDFDocument(url: URL(fileURLWithPath: path)) else {
        return Doc(path: path, pageCount: 0, totalChars: 0, pagesWithText: 0,
                   pages: [], error: "unreadable")
    }
    var pages: [Page] = []
    for i in 0..<doc.pageCount {
        let s = doc.page(at: i)?.string ?? ""
        pages.append(Page(page: i + 1, chars: s.count, text: s))
    }
    let total = pages.reduce(0) { $0 + $1.chars }
    let withText = pages.filter { $0.chars > 0 }.count
    return Doc(path: path, pageCount: doc.pageCount, totalChars: total,
               pagesWithText: withText, pages: pages, error: nil)
}

let paths = CommandLine.arguments.dropFirst()
if paths.isEmpty {
    FileHandle.standardError.write("usage: pdfpages <pdf> [<pdf>...]\n".data(using: .utf8)!)
    exit(1)
}

for path in paths {
    if let data = try? encoder.encode(dump(path)),
       let line = String(data: data, encoding: .utf8) {
        print(line)
        fflush(stdout)
    }
}
