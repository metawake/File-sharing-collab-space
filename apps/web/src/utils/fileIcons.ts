/**
 * Get emoji icon for file type based on mime type
 */
export function getFileIcon(mimeType: string | null | undefined): string {
  if (!mimeType) return '📄';
  
  // PDF
  if (mimeType.includes('pdf')) return '📄';
  
  // Word documents
  if (mimeType.includes('word') || mimeType.includes('msword') || 
      mimeType.includes('document') || mimeType.endsWith('.docx')) return '📝';
  
  // Excel spreadsheets
  if (mimeType.includes('excel') || mimeType.includes('spreadsheet') || 
      mimeType.endsWith('.xlsx')) return '📊';
  
  // PowerPoint presentations
  if (mimeType.includes('powerpoint') || mimeType.includes('presentation') ||
      mimeType.endsWith('.pptx')) return '📊';
  
  // Images
  if (mimeType.startsWith('image/')) return '🖼️';
  
  // Video
  if (mimeType.startsWith('video/')) return '🎥';
  
  // Audio
  if (mimeType.startsWith('audio/')) return '🎵';
  
  // Archives
  if (mimeType.includes('zip') || mimeType.includes('rar') || 
      mimeType.includes('7z') || mimeType.includes('tar')) return '📦';
  
  // Text files
  if (mimeType.startsWith('text/')) return '📃';
  
  // Default
  return '📄';
}

/**
 * Get human-readable file type label
 */
export function getFileTypeLabel(mimeType: string | null | undefined): string {
  if (!mimeType) return 'File';
  
  if (mimeType.includes('pdf')) return 'PDF';
  if (mimeType.includes('word') || mimeType.includes('msword')) return 'Word';
  if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'Excel';
  if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'PowerPoint';
  if (mimeType.startsWith('image/')) return 'Image';
  if (mimeType.startsWith('video/')) return 'Video';
  if (mimeType.startsWith('audio/')) return 'Audio';
  if (mimeType.includes('zip') || mimeType.includes('rar')) return 'Archive';
  if (mimeType.startsWith('text/')) return 'Text';
  
  return 'File';
}

