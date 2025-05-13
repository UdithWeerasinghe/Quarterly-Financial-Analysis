export function getLastQuarterDataPerYear(data) {
  const map = new Map();
  data.forEach((d) => {
    const year = new Date(d.TableDate).getFullYear();
    map.set(year, d); // Overwrite, so last stays
  });
  return Array.from(map.values()).sort((a, b) => new Date(a.TableDate) - new Date(b.TableDate));
} 