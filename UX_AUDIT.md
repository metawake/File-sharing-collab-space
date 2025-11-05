# UX Audit: HarvyAI DataRoom
**Context:** Legal document management system for secure file sharing  
**Date:** November 5, 2025  
**Focus:** Professional polish, legal industry best practices, workflow optimization

---

## Executive Summary

**Overall Assessment:** ✅ Good foundation, needs professional refinement

**Strengths:**
- Clear role-based access control
- Good sectioning with visual hierarchy
- Responsive feedback (toasts, loading states)
- Auto-selection of Demo Room for guests

**Critical Issues:**
- ⚠️ No clear value proposition or branding
- ⚠️ Missing file type indicators and document previews
- ⚠️ Insufficient permission/role explanations
- ⚠️ No member management visibility (can't see current members)
- ⚠️ Room creation flow too minimal for legal context

---

## Detailed Findings

### 1. ❌ **BRANDING & VALUE PROPOSITION**

**Issue:** Header says "DataRoom Service" (generic) + emoji. No clear identity or value proposition.

**Legal Context:** Law firms need professional, trustworthy interfaces. Current design feels consumer-grade.

**Recommendations:**
- Replace emoji with professional icon or logo
- Add tagline: "Secure Document Sharing for Legal Professionals"
- Include security indicator (🔒 Encrypted / SOC 2 Compliant)
- Better branding in browser title

---

### 2. ⚠️ **WELCOME MESSAGE** (Low Priority for Logged-In Users)

**Issue:** Welcome section takes prime real estate for authenticated users with generic message.

**Fix:**
- For logged-in users: Show quick stats (X rooms, Y files, Last accessed: ...)
- For guests: Current message is fine
- Add quick action buttons: "Create Room" / "Import Files"

---

### 3. 🔴 **ROOM CREATION - TOO MINIMAL FOR LEGAL USE**

**Issue:** Just "Room name" input. Legal data rooms need context.

**Missing:**
- Case/Client ID
- Matter type (Litigation, M&A, Due Diligence, etc.)
- Privacy level indicator
- Description/Purpose field
- Who is this for? (Internal team / Client access / Third party)

**Recommendation:**
```
Create New Data Room
┌────────────────────────────────────┐
│ Room Name*                         │
│ [Case #2024-045: Smith v. Jones]   │
│                                     │
│ Matter Type                         │
│ [Litigation ▼]                      │
│                                     │
│ Description (optional)              │
│ [Confidential case files...]        │
│                                     │
│ Initial Members (optional)          │
│ [email@firm.com] [Viewer ▼] [+ Add]│
│                                     │
│ [Cancel]          [Create Room →]  │
└────────────────────────────────────┘
```

---

### 4. 🔴 **MEMBER MANAGEMENT - NO VISIBILITY**

**Critical Issue:** You can ADD members, but can't SEE current members!

**Missing:**
- List of current members with roles
- Last accessed timestamp
- Remove member capability
- Change role capability
- Member invitation status (pending/accepted)

**Fix:** Add table below "Add member" form:

```
Current Members (3)
┌────────────────────────────────────────────────────┐
│ Email             Role    Joined      Last Access  │
│ you@firm.com      Owner   Jan 2024    2 min ago    │
│ partner@firm.com  Admin   Jan 2024    Yesterday    │
│ client@corp.com   Viewer  Feb 2024    3 days ago   │
└────────────────────────────────────────────────────┘
```

---

### 5. ⚠️ **ROLE DESCRIPTIONS - NOT CLEAR**

**Issue:** Dropdown shows "Viewer / Editor / Admin" with no explanation.

**Legal Context:** Permissions are critical. Users need to understand implications.

**Fix:** Add tooltip/help text:

```
Role: [Viewer ▼] ⓘ

Tooltip on hover:
• Viewer: Download files only
• Editor: Upload & download files
• Admin: Full control except deleting room
• Owner: Complete control (auto-assigned on creation)
```

---

### 6. ⚠️ **FILE TABLE - MISSING KEY FEATURES**

**Issues:**
- No file type icons (📄 PDF, 📊 Excel, 📝 Word)
- No preview capability (legal docs often need quick review)
- No file version indicator
- No "Added by" column
- No upload date vs. modified date distinction
- Download button could be clearer ("Download" not just icon)

**Recommendations:**

```
Files in Case #2024-045 (12)                [+ Import Files]

┌──────────────────────────────────────────────────────────────────────┐
│ 📄 Name              Type   Size    Uploaded     Uploaded By   Actions│
│ ○ Complaint.pdf      PDF    2.3 MB  Jan 5, 2024  you@firm.com  ⬇️ 👁️  │
│ ○ Evidence_A.docx    Word   156 KB  Jan 6, 2024  partner@...   ⬇️ 👁️  │
│ ○ Deposition.mp4     Video  89 MB   Jan 7, 2024  you@firm.com  ⬇️     │
└──────────────────────────────────────────────────────────────────────┘

⬇️ = Download  👁️ = Preview  🗑️ = Delete
```

---

### 7. ⚠️ **IMPORT WORKFLOW - UNCLEAR PURPOSE**

**Issues:**
- "Import into [Room Name]" - not clear what "import" means
- Placeholder text too technical: "Paste Drive URL(s) or raw ID(s)"
- No visual indicator of what happens to files
- No file preview before importing

**Better Wording:**
```
📥 Add Files from Google Drive

Select files to securely import into this data room. Files will be 
encrypted and accessible only to authorized members.

┌─────────────────────────────────────────────────────┐
│ Google Drive File URLs (one per line or comma-sep)  │
│ [https://drive.google.com/file/d/...]               │
└─────────────────────────────────────────────────────┘

[📁 Browse My Drive]  [Import Files →]

✓ Files are encrypted at rest
✓ Audit log tracks all access
✓ Original files remain in your Drive
```

---

### 8. ⚠️ **NO AUDIT LOG / ACTIVITY FEED**

**Issue:** Legal compliance requires visibility into who accessed what.

**Missing:** Activity log visible to room owners/admins

**Add Section:**
```
📊 Recent Activity (Last 7 days)

Jan 7, 2024  10:45 AM  partner@firm.com downloaded Complaint.pdf
Jan 7, 2024  09:12 AM  client@corp.com viewed Evidence_A.docx
Jan 6, 2024  04:30 PM  you@firm.com added 3 files
Jan 5, 2024  02:15 PM  you@firm.com invited client@corp.com as Viewer

[View Full Audit Log →]
```

---

### 9. ✅ **ROOM NAVIGATION - GOOD BUT CAN IMPROVE**

**Current:** "← Back to rooms" button works well

**Enhancement:** Breadcrumbs for clarity
```
DataRoom Service > Case #2024-045 > Files
```

---

### 10. ⚠️ **NO SEARCH / FILTER**

**Issue:** Once you have 20+ files, finding documents becomes hard.

**Add:**
```
Files in Case #2024-045

┌────────────────────────────┐  Filter: [All Types ▼] [All Users ▼]
│ 🔍 Search files...         │  Sort: [Date ▼]
└────────────────────────────┘
```

---

### 11. ⚠️ **EMPTY STATES**

**Current:** "No files yet." (bland)

**Better Empty States:**

```
📄 No Files Yet

This data room is empty. Get started by importing files 
from Google Drive or creating your first folder.

[Import from Drive →]  [Learn More]
```

---

### 12. ⚠️ **NO CONFIRMATION ON CRITICAL ACTIONS**

**Issue:** Room creation happens instantly (could be accidental)

**Add confirmations for:**
- Deleting room (currently not possible, but should be)
- Removing members
- Changing member roles

---

### 13. ✅ **GUEST EXPERIENCE - GOOD**

**Current:** Auto-shows Demo Room, clear banner about guest status

**Enhancement:** Add call-to-action value props
```
👁️ You're viewing the Demo Room as a guest.

Sign in to:
✓ Create unlimited secure data rooms
✓ Import files from Google Drive
✓ Invite team members & clients
✓ Track document access with audit logs

[Sign in with Google →]
```

---

### 14. ⚠️ **MOBILE RESPONSIVENESS** (Assumption - Not Tested)

**Concern:** Legal professionals often review documents on tablets/phones.

**Check:**
- Table horizontal scroll on mobile
- Touch targets 44x44px minimum
- Forms stack vertically
- File names truncate gracefully

---

### 15. ⚠️ **NO HELP / DOCUMENTATION LINK**

**Issue:** No way to get help or understand features.

**Add to header:**
```
[Help] [Contact Support]
```

---

## Priority Fixes (Ranked)

### 🔴 **CRITICAL (Do First)**

1. **Add Member List** - Can't see who has access (security issue)
2. **File Type Icons** - Visual clarity for document types
3. **Role Descriptions** - Clear permission explanations
4. **Branding** - Professional identity

### 🟡 **HIGH PRIORITY**

5. **Room Creation Flow** - Add case/matter context
6. **Activity Log** - Compliance requirement
7. **Search/Filter Files** - Usability at scale
8. **Import Wording** - Clearer language

### 🟢 **NICE TO HAVE**

9. **Quick Stats Dashboard** - For logged-in users
10. **Better Empty States** - Engaging & educational
11. **Breadcrumbs** - Navigation clarity
12. **File Preview** - Quick document review

---

## Legal Industry Best Practices Checklist

- [ ] Clear permission model (owner/admin/editor/viewer) ✅ Done
- [ ] Audit logging visible to admins ❌ Backend exists, no UI
- [ ] Member management transparency ❌ Can't see members
- [ ] Document version control ❌ Not implemented
- [ ] Encryption indicators ❌ No trust signals
- [ ] Access expiration (optional) ❌ Not implemented
- [ ] Watermarking (optional) ❌ Not implemented
- [ ] Bulk actions (select multiple files) ❌ Not implemented
- [ ] Export capability (download all) ❌ Not implemented
- [ ] Professional branding ⚠️ Too casual

---

## Wireframe: Improved Room View (Owner Perspective)

```
┌────────────────────────────────────────────────────────────────┐
│ 🔒 HarvyAI DataRoom   Secure Document Sharing for Legal Teams  │
│                                                                  │
│ DataRoom Service > Case #2024-045                    [Help]     │
│ Signed in as: you@firm.com         [🔔 3] [Sign out]           │
└────────────────────────────────────────────────────────────────┘

┌─ Room Overview ──────────────────────────────────────────────┐
│ 📁 Case #2024-045: Smith v. Jones Litigation                 │
│ Created: Jan 5, 2024  •  Matter Type: Litigation             │
│ Your Role: Owner  •  3 Members  •  12 Files (2.3 GB)         │
│                                                                │
│ [← Back to Rooms]  [⚙️ Room Settings]  [📊 Activity Log]     │
└────────────────────────────────────────────────────────────────┘

┌─ 👥 Members (3) ─────────────────────────────────────────────┐
│ you@firm.com          Owner    Jan 5   2 min ago    [—]      │
│ partner@firm.com      Admin    Jan 5   Yesterday    [Edit ▼] │
│ client@corp.com       Viewer   Jan 6   3 days ago   [Edit ▼] │
│                                                                │
│ Add Member: [email@example.com] [Viewer ▼] ⓘ [Invite →]     │
└────────────────────────────────────────────────────────────────┘

┌─ 📥 Add Files from Google Drive ─────────────────────────────┐
│ [https://drive.google.com/...] [📁 Browse] [Import →]        │
│ ✓ Encrypted  ✓ Audit logged  ✓ Originals stay in Drive      │
└────────────────────────────────────────────────────────────────┘

┌─ 📄 Files (12) ───────────────────────────────────────────────┐
│ [🔍 Search...]  Type: [All ▼]  Uploaded by: [All ▼]          │
│                                                                │
│ Name ▼         Type  Size   Uploaded     By             ⬇️ 👁️│
│ 📄 Complaint    PDF   2.3MB  Jan 5, 2024  you@firm.com   ✓  ✓│
│ 📝 Brief.docx   Word  156KB  Jan 6, 2024  partner@...    ✓  ✓│
│ 📊 Analysis     Excel 89KB   Jan 7, 2024  you@firm.com   ✓  ✓│
└────────────────────────────────────────────────────────────────┘

┌─ 📊 Recent Activity (Last 7 days) ───────────────────────────┐
│ Jan 7  10:45 AM  partner@firm.com downloaded Brief.docx      │
│ Jan 7  09:12 AM  client@corp.com viewed Complaint.pdf        │
│ [View Full Audit Log →]                                       │
└────────────────────────────────────────────────────────────────┘
```

---

## Conclusion

**Current State:** Functional MVP with good bones  
**Target State:** Professional legal-grade interface

**Estimated Impact:**
- **Professionalism:** ⭐⭐⭐ → ⭐⭐⭐⭐⭐ (with branding + polish)
- **Usability:** ⭐⭐⭐⭐ → ⭐⭐⭐⭐⭐ (with member list + search)
- **Trust:** ⭐⭐ → ⭐⭐⭐⭐⭐ (with security indicators + audit log)

**Next Steps:** Implement Critical fixes first, then iterate on High Priority items.

