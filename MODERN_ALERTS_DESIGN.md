# 🎨 Modern Alerts Design - Notion Style

## Overview
Complete redesign with **Notion/Nike/Perplexity-inspired** minimalist aesthetic.

---

## ✨ Design Principles

### 1. **Minimal & Clean**
- Remove all unnecessary containers
- Embrace white space
- Simple, flat design
- No heavy shadows or gradients

### 2. **Typography-First**
- Clear hierarchy with font sizes
- Modern font weights (600 for headers, 500 for labels)
- Subtle colors (#1a1a1a for text, #8e8e8e for secondary)

### 3. **Compact Buttons**
- NOT full-width
- Side-by-side layout
- Clear visual hierarchy (primary/secondary/ghost)
- Small, modern padding

### 4. **Subtle Interactions**
- Minimal hover effects
- 2px lift on hover
- Soft purple accent (#6c5ce7)
- Quick transitions (0.2s)

---

## 🎯 Alert Cards

### Structure
```
┌─────────────────────────────────────────────┐
│ Company Name              📈 Pattern Break  │
│ Subtitle                                    │
│                                             │
│ Customer typically orders every 2 days but  │
│ is now 17 days overdue                      │
│                                             │
│ 19d          4            €0.4k             │
│ Since order  Orders       Value             │
│ ─────────────────────────────────────────── │
│ [Contact] [Invoices] [Dismiss]              │
└─────────────────────────────────────────────┘
```

### Key Features
- **Clean header** - company name + tag
- **One-line description** - clear and direct
- **Inline metrics** - compact, just the numbers
- **Three buttons** - equal width, modern style

---

## 🎨 Color Palette

### Primary
- **Purple**: #6c5ce7 (buttons, accents)
- **Text**: #1a1a1a (primary text)
- **Secondary**: #8e8e8e (labels, subtle text)
- **Border**: #e9ecef (card borders)

### Tags
- **Pattern Break**: Orange (#e67700 on #fff4e6)
- **High Value**: Red (#d32f2f on #ffe5e5)
- **Dormant**: Gray (#424242 on #f0f0f0)
- **Declining**: Blue (#1976d2 on #e3f2fd)
- **Less Frequent**: Purple (#5e35b1 on #e8eaf6)
- **One-Timer**: Gray (#757575 on #f5f5f5)
- **Outstanding**: Red (#c62828 on #ffebee)

---

## 🔘 Button Styles

### Primary (Contact)
```css
background: #6c5ce7
color: white
padding: 6px 14px
border-radius: 6px
```

### Secondary (Invoices)
```css
background: #f0f0f0
color: #1a1a1a
padding: 6px 14px
border-radius: 6px
```

### Ghost (Dismiss)
```css
background: transparent
color: #8e8e8e
padding: 6px 14px
border-radius: 6px
```

---

## 📱 Modal Design

### Enhanced Modal
- Clean header with company name
- Tags at top (alert type + priority)
- Spacious description
- Metrics in grid (3 columns)
- Recommendation in styled box
- Contact info at bottom
- Two action buttons in footer

### Modal Actions
1. **Contact Customer** - Opens email, closes modal
2. **View Invoices** - Navigates to Data page, auto-filters, closes modal

---

## 🔄 View Invoices Flow

### User Journey
1. User clicks **"Invoices"** button on alert
2. System stores company ID in sessionStorage
3. Navigates to `/data` page
4. Data page detects stored ID
5. Loads company data
6. Finds company card with `data-company-id` attribute
7. Scrolls smoothly to company
8. Auto-clicks to open invoice details
9. Shows toast notification

### Technical Flow
```javascript
// Alerts page
viewCompanyInvoices(companyId, companyName) {
    sessionStorage.setItem('filterCompanyId', companyId);
    sessionStorage.setItem('filterCompanyName', companyName);
    window.location.href = '/data';
}

// Data page
if (filterCompanyId) {
    loadData().then(() => {
        const element = document.querySelector(`[data-company-id="${filterCompanyId}"]`);
        element.scrollIntoView({ behavior: 'smooth' });
        element.click(); // Opens invoice modal
    });
}
```

---

## 📐 Spacing & Sizing

### Card
- Padding: 20px
- Margin bottom: 16px (between elements)
- Border radius: 8px
- Border: 1px solid #e9ecef

### Metrics
- Value: 20px, font-weight 600
- Label: 11px, uppercase, #8e8e8e
- Gap: 24px between metrics

### Buttons
- Height: auto (6px vertical padding)
- Width: auto (14px horizontal padding)
- Gap: 8px between buttons
- Font: 13px, weight 500

---

## 🎯 Typography Scale

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Company Name | 16px | 600 | #1a1a1a |
| Subtitle | 13px | 400 | #8e8e8e |
| Description | 14px | 400 | #4a4a4a |
| Metric Value | 20px | 600 | #1a1a1a |
| Metric Label | 11px | 500 | #8e8e8e |
| Tag | 11px | 500 | varies |
| Button | 13px | 500 | varies |

---

## ✅ What's Fixed

1. ✅ **Removed nested containers** - flat, clean structure
2. ✅ **Clear visual hierarchy** - typography-based
3. ✅ **Compact buttons** - NO full-width
4. ✅ **Modal restored** - click card to see details
5. ✅ **View Invoices works** - auto-filters and opens
6. ✅ **Modern aesthetics** - Notion/Nike inspired
7. ✅ **Minimal design** - less is more

---

## 🎨 Before vs After

### Before
- Multiple nested containers
- Heavy shadows and gradients
- Full-width buttons
- Cluttered metrics with icons
- Too much visual weight

### After
- Single-level structure
- Subtle borders, minimal shadows
- Compact, proportional buttons
- Clean inline metrics
- Breathable design

---

## 🚀 Result

A **professional, modern, minimalist** alerts interface that:
- Looks like a proper SaaS product
- Follows modern design trends
- Provides excellent UX
- Works seamlessly with data page
- Feels fast and responsive

**This is the Notion-style you asked for!** 🎉

