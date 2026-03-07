//
//  InvoiceKitsWidgetBundle.swift
//  InvoiceKitsWidget
//
//  Created by Ryan Pate on 3/7/26.
//

import WidgetKit
import SwiftUI

@main
struct InvoiceKitsWidgetBundle: WidgetBundle {
    var body: some Widget {
        InvoiceKitsWidget()
        InvoiceKitsWidgetLiveActivity()
    }
}
