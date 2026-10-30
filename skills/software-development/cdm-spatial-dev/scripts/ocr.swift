// ocr.swift — read TEXT out of a screenshot when vision_analyze is 404ing.
//
//   cp "<screencapture path with spaces>" /tmp/shot.png
//   swift scripts/ocr.swift /tmp/shot.png
//
// Prints every recognised line as:  [x=0.203 ybot=0.008] the text
// Vision boxes are BOTTOM-UP, so a bottom-left HUD/debug chip has a SMALL ybot
// and a top header has a LARGE one — that is how you tell WHERE text sat
// without seeing the image. This is how to read an on-screen diagnostic chip
// yourself, with no vision tool and no round-trip asking the user.
//
// macOS Vision framework (Xcode CLT). No tesseract, no install.
// TEXT ONLY: colours, layout, and whether a 3D render actually succeeded are
// NOT recoverable from OCR — state that and ask the user instead of inferring.

import Vision
import Foundation
import AppKit

let args = CommandLine.arguments
let path = args.count > 1 ? args[1] : "/tmp/shot.png"

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(1)
}

guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fail("could not load image at: \(path)")
}

let req = VNRecognizeTextRequest { request, error in
    if let error = error { fail("OCR error: \(error)") }
    guard let obs = request.results as? [VNRecognizedTextObservation] else { return }
    for o in obs.sorted(by: { $0.boundingBox.origin.y < $1.boundingBox.origin.y }) {
        guard let c = o.topCandidates(1).first else { continue }
        let b = o.boundingBox
        print(String(format: "[x=%.3f ybot=%.3f] %@", b.origin.x, b.origin.y, c.string))
    }
}
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do { try handler.perform([req]) } catch { fail("perform failed: \(error)") }
