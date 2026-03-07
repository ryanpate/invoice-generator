//
//  InvoiceKitsWidgetLiveActivity.swift
//  InvoiceKitsWidget
//
//  Created by Ryan Pate on 3/7/26.
//

import ActivityKit
import WidgetKit
import SwiftUI

struct InvoiceKitsWidgetAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        // Dynamic stateful properties about your activity go here!
        var emoji: String
    }

    // Fixed non-changing properties about your activity go here!
    var name: String
}

struct InvoiceKitsWidgetLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: InvoiceKitsWidgetAttributes.self) { context in
            // Lock screen/banner UI goes here
            VStack {
                Text("Hello \(context.state.emoji)")
            }
            .activityBackgroundTint(Color.cyan)
            .activitySystemActionForegroundColor(Color.black)

        } dynamicIsland: { context in
            DynamicIsland {
                // Expanded UI goes here.  Compose the expanded UI through
                // various regions, like leading/trailing/center/bottom
                DynamicIslandExpandedRegion(.leading) {
                    Text("Leading")
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text("Trailing")
                }
                DynamicIslandExpandedRegion(.bottom) {
                    Text("Bottom \(context.state.emoji)")
                    // more content
                }
            } compactLeading: {
                Text("L")
            } compactTrailing: {
                Text("T \(context.state.emoji)")
            } minimal: {
                Text(context.state.emoji)
            }
            .widgetURL(URL(string: "http://www.apple.com"))
            .keylineTint(Color.red)
        }
    }
}

extension InvoiceKitsWidgetAttributes {
    fileprivate static var preview: InvoiceKitsWidgetAttributes {
        InvoiceKitsWidgetAttributes(name: "World")
    }
}

extension InvoiceKitsWidgetAttributes.ContentState {
    fileprivate static var smiley: InvoiceKitsWidgetAttributes.ContentState {
        InvoiceKitsWidgetAttributes.ContentState(emoji: "😀")
     }
     
     fileprivate static var starEyes: InvoiceKitsWidgetAttributes.ContentState {
         InvoiceKitsWidgetAttributes.ContentState(emoji: "🤩")
     }
}

#Preview("Notification", as: .content, using: InvoiceKitsWidgetAttributes.preview) {
   InvoiceKitsWidgetLiveActivity()
} contentStates: {
    InvoiceKitsWidgetAttributes.ContentState.smiley
    InvoiceKitsWidgetAttributes.ContentState.starEyes
}
