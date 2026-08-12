// Render PDF pages to PNG at a chosen scale, for OCR comparison and for page
// images if the migration ends up wanting them embedded in the vault.
// Usage: render <pdf> <outdir> <scale> [maxPages]

import Foundation
import PDFKit
import AppKit

let args = CommandLine.arguments
guard args.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("usage: render <pdf> <outdir> [scale]\n".data(using: .utf8)!)
    exit(1)
}
let outdir = args[2]
let scale = args.count > 3 ? (Double(args[3]) ?? 2.0) : 2.0
try? FileManager.default.createDirectory(atPath: outdir, withIntermediateDirectories: true)

let stem = URL(fileURLWithPath: args[1]).deletingPathExtension().lastPathComponent

// A page cap keeps thumbnail passes cheap: Search App is 182 pages and the panel
// only ever shows the first few.
let limit = args.count > 4 ? min(Int(args[4]) ?? doc.pageCount, doc.pageCount) : doc.pageCount

for i in 0..<limit {
    guard let page = doc.page(at: i) else { continue }
    let rect = page.bounds(for: .mediaBox)
    let size = NSSize(width: rect.width * scale, height: rect.height * scale)
    let image = page.thumbnail(of: size, for: .mediaBox)
    guard let tiff = image.tiffRepresentation,
          let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else { continue }
    let path = "\(outdir)/\(stem)-p\(String(format: "%02d", i + 1)).png"
    try? png.write(to: URL(fileURLWithPath: path))
    print(path)
}
