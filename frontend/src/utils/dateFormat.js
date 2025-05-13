export const formatDate = (dateString, isAnnual, index, data) => {
  const date = new Date(dateString);
  
  if (isAnnual) {
    const year = date.getFullYear();
    // Show year only for the last data point of the year
    const isLastOfYear =
      index === data.length - 1 ||
      new Date(data[index + 1].TableDate).getFullYear() !== year;
    return isLastOfYear ? year.toString() : '';
  }
  
  // For quarterly view, show all dates
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}; 