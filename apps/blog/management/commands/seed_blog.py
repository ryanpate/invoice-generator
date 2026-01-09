"""
Management command to seed initial blog posts.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.blog.models import BlogPost, BlogCategory


class Command(BaseCommand):
    help = 'Seeds initial blog posts for SEO content'

    def handle(self, *args, **options):
        User = get_user_model()

        # Get or create admin user as author
        author = User.objects.filter(is_superuser=True).first()
        if not author:
            self.stdout.write(self.style.WARNING('No superuser found. Skipping blog seed.'))
            return

        # Create categories
        guides_category, _ = BlogCategory.objects.get_or_create(
            slug='guides',
            defaults={
                'name': 'Guides',
                'description': 'Step-by-step guides for invoicing and billing'
            }
        )

        tips_category, _ = BlogCategory.objects.get_or_create(
            slug='tips',
            defaults={
                'name': 'Tips & Best Practices',
                'description': 'Expert tips for freelancers and small businesses'
            }
        )

        # Create first blog post
        post_slug = 'how-to-create-professional-invoice'
        if BlogPost.objects.filter(slug=post_slug).exists():
            self.stdout.write(self.style.WARNING(f'Blog post "{post_slug}" already exists. Skipping.'))
            return

        post_content = '''
<p class="text-xl text-gray-700 dark:text-gray-300 mb-8">Creating a professional invoice doesn't have to be complicated. Whether you're a freelancer sending your first invoice or a small business owner looking to streamline your billing process, this comprehensive guide will walk you through everything you need to know about creating invoices that get you paid faster.</p>

<h2 class="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4">What Is an Invoice?</h2>

<p class="mb-4">An invoice is a commercial document that itemizes a transaction between a buyer and seller. It serves as a formal request for payment and includes details about the products or services provided, quantities, prices, and payment terms.</p>

<p class="mb-4">A well-crafted invoice does more than request payment—it reinforces your professionalism, provides clear documentation for both parties, and helps maintain healthy cash flow for your business.</p>

<h2 class="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4">Essential Elements Every Invoice Must Include</h2>

<p class="mb-4">To create a professional invoice that meets legal requirements and ensures prompt payment, include these key elements:</p>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">1. Your Business Information</h3>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li>Business name and logo</li>
    <li>Contact information (address, phone, email)</li>
    <li>Tax identification number (if applicable)</li>
</ul>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">2. Client Information</h3>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li>Client's full name or business name</li>
    <li>Billing address</li>
    <li>Contact email</li>
</ul>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">3. Invoice Details</h3>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li><strong>Invoice number:</strong> A unique identifier for tracking</li>
    <li><strong>Invoice date:</strong> When the invoice was issued</li>
    <li><strong>Due date:</strong> When payment is expected</li>
    <li><strong>Payment terms:</strong> Net 30, Net 15, Due on Receipt, etc.</li>
</ul>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">4. Itemized List of Services or Products</h3>
<p class="mb-4">Break down each service or product with:</p>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li>Clear description</li>
    <li>Quantity or hours</li>
    <li>Rate or unit price</li>
    <li>Line item total</li>
</ul>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">5. Financial Summary</h3>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li>Subtotal</li>
    <li>Taxes (if applicable)</li>
    <li>Discounts (if any)</li>
    <li><strong>Total amount due</strong></li>
</ul>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">6. Payment Instructions</h3>
<p class="mb-4">Make it easy for clients to pay by including:</p>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li>Accepted payment methods</li>
    <li>Bank details or payment link</li>
    <li>Late payment penalties (if applicable)</li>
</ul>

<h2 class="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4">Step-by-Step: How to Create an Invoice</h2>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Step 1: Choose Your Invoice Method</h3>
<p class="mb-4">You have several options for creating invoices:</p>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li><strong>Invoice generator software</strong> (like InvoiceKits) - Fastest and most professional</li>
    <li>Word processor templates - Basic but time-consuming</li>
    <li>Spreadsheet programs - Flexible but requires manual formatting</li>
    <li>Accounting software - Full-featured but often expensive</li>
</ul>

<p class="mb-4">Using a dedicated <strong>invoice generator</strong> like InvoiceKits saves time and ensures consistency across all your invoices.</p>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Step 2: Add Your Branding</h3>
<p class="mb-4">Upload your logo and set your business colors. Consistent branding makes your invoices instantly recognizable and reinforces your professional image.</p>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Step 3: Enter Client Details</h3>
<p class="mb-4">Fill in your client's information accurately. Double-check spelling and addresses to avoid payment delays.</p>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Step 4: Add Line Items</h3>
<p class="mb-4">List each product or service separately. Be specific in your descriptions—instead of "Consulting," write "Marketing Strategy Consultation - Q1 Campaign Planning."</p>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Step 5: Set Payment Terms</h3>
<p class="mb-4">Common payment terms include:</p>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li><strong>Due on Receipt:</strong> Payment expected immediately</li>
    <li><strong>Net 15:</strong> Payment due within 15 days</li>
    <li><strong>Net 30:</strong> Payment due within 30 days (most common)</li>
    <li><strong>Net 60:</strong> Payment due within 60 days</li>
</ul>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Step 6: Review and Send</h3>
<p class="mb-4">Before sending, review your invoice for:</p>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li>Correct calculations</li>
    <li>Accurate client information</li>
    <li>Clear payment instructions</li>
    <li>Professional formatting</li>
</ul>

<h2 class="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4">Invoice Best Practices for Faster Payments</h2>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Send Invoices Promptly</h3>
<p class="mb-4">Send your invoice as soon as work is completed. The sooner you invoice, the sooner you get paid. Studies show that invoices sent within 24 hours of project completion are paid 1.5x faster.</p>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Use Clear, Professional Language</h3>
<p class="mb-4">Avoid jargon and be specific about what you're billing for. Clarity reduces questions and disputes that delay payment.</p>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Offer Multiple Payment Options</h3>
<p class="mb-4">The easier you make it to pay, the faster you'll receive payment. Consider accepting:</p>
<ul class="list-disc pl-6 mb-4 space-y-2">
    <li>Bank transfers</li>
    <li>Credit cards</li>
    <li>PayPal or other digital wallets</li>
    <li>Checks (for traditional clients)</li>
</ul>

<h3 class="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">Follow Up on Overdue Invoices</h3>
<p class="mb-4">Don't be afraid to send payment reminders. A polite follow-up email a few days after the due date can significantly improve collection rates.</p>

<h2 class="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4">Common Invoice Mistakes to Avoid</h2>

<ul class="list-disc pl-6 mb-4 space-y-2">
    <li><strong>Missing or unclear payment terms:</strong> Always specify when payment is due</li>
    <li><strong>Vague descriptions:</strong> Be specific about what services were rendered</li>
    <li><strong>Math errors:</strong> Double-check all calculations</li>
    <li><strong>Missing contact information:</strong> Make it easy for clients to reach you with questions</li>
    <li><strong>Inconsistent numbering:</strong> Use a sequential invoice numbering system</li>
    <li><strong>Forgetting taxes:</strong> Include applicable sales tax or VAT</li>
</ul>

<h2 class="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4">Free Invoice Template vs. Invoice Generator Software</h2>

<p class="mb-4">While free invoice templates can work for occasional invoicing, an <strong>invoice generator</strong> offers significant advantages for growing businesses:</p>

<div class="overflow-x-auto mb-6">
<table class="min-w-full border border-gray-200 dark:border-gray-700">
    <thead class="bg-gray-50 dark:bg-gray-800">
        <tr>
            <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white border-b">Feature</th>
            <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white border-b">Free Template</th>
            <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white border-b">Invoice Generator</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="px-4 py-3 border-b dark:border-gray-700">Auto-numbering</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Manual</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Automatic</td>
        </tr>
        <tr>
            <td class="px-4 py-3 border-b dark:border-gray-700">Calculations</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Manual</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Automatic</td>
        </tr>
        <tr>
            <td class="px-4 py-3 border-b dark:border-gray-700">Client management</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">None</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Built-in</td>
        </tr>
        <tr>
            <td class="px-4 py-3 border-b dark:border-gray-700">Payment tracking</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Manual</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Automatic</td>
        </tr>
        <tr>
            <td class="px-4 py-3 border-b dark:border-gray-700">Batch invoicing</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">Not possible</td>
            <td class="px-4 py-3 border-b dark:border-gray-700">CSV upload</td>
        </tr>
        <tr>
            <td class="px-4 py-3">Time to create</td>
            <td class="px-4 py-3">10-15 minutes</td>
            <td class="px-4 py-3">Under 2 minutes</td>
        </tr>
    </tbody>
</table>
</div>

<h2 class="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4">Start Creating Professional Invoices Today</h2>

<p class="mb-4">Creating professional invoices is essential for maintaining healthy cash flow and projecting a professional image. With the right tools and best practices, you can streamline your invoicing process and get paid faster.</p>

<p class="mb-4">Ready to create your first professional invoice? <a href="/accounts/signup/" class="text-primary-600 dark:text-primary-400 hover:underline font-medium">Sign up for InvoiceKits free</a> and create unlimited professional invoices in minutes—no credit card required.</p>

<div class="bg-gray-100 dark:bg-gray-800 rounded-lg p-6 mt-8">
    <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Key Takeaways</h3>
    <ul class="list-disc pl-6 space-y-1 text-gray-700 dark:text-gray-300">
        <li>Include all essential elements: business info, client details, itemized list, and payment terms</li>
        <li>Send invoices promptly—within 24 hours of completing work</li>
        <li>Use clear, specific descriptions for line items</li>
        <li>Offer multiple payment options to make paying easy</li>
        <li>Use an invoice generator to save time and maintain consistency</li>
    </ul>
</div>
'''

        BlogPost.objects.create(
            title='How to Create a Professional Invoice in 2026 (Complete Guide)',
            slug=post_slug,
            author=author,
            category=guides_category,
            excerpt='Learn how to create professional invoices that get you paid faster. This step-by-step guide covers everything from essential invoice elements to best practices for freelancers and small businesses.',
            content=post_content,
            meta_description='Learn how to create a professional invoice in 2026. Step-by-step guide covering essential elements, best practices, and tips to get paid faster as a freelancer or small business.',
            meta_keywords='how to create an invoice, invoice template, professional invoice, invoice generator, freelance invoice, small business invoice, invoice best practices',
            status='published',
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully created blog post: "{post_slug}"'))
