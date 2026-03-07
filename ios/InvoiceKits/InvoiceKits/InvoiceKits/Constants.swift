import Foundation

enum Constants {
    static let apiBaseURL = URL(string: "https://www.invoicekits.com/api/v2")!

    enum StoreKit {
        static let proMonthly = "com.invoicekits.pro.monthly"
        static let proAnnual = "com.invoicekits.pro.annual"
        static let businessMonthly = "com.invoicekits.business.monthly"
        static let businessAnnual = "com.invoicekits.business.annual"
        static let credits10 = "com.invoicekits.credits.10"
        static let credits25 = "com.invoicekits.credits.25"
        static let credits50 = "com.invoicekits.credits.50"

        static let subscriptionIDs = [proMonthly, proAnnual, businessMonthly, businessAnnual]
        static let creditIDs = [credits10, credits25, credits50]
    }
}
