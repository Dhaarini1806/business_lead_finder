"""
Website Analyzer Service — Check SSL, SEO, performance, and mobile responsiveness.

Features:
- SSL/HTTPS certificate validation
- Basic SEO metrics (meta tags, H1, sitemap)
- Page load time estimation
- Mobile responsiveness check
- Generates recommendations
"""

import re
import time
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class WebsiteAnalyzer:
    """Analyze website health and generate recommendations."""
    
    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FORGE.OS Website Analyzer / 1.0"
        })
        self.results = {
            "url": url,
            "has_ssl": False,
            "ssl_valid": False,
            "ssl_expires_at": None,
            "seo_score": 0,
            "has_meta_description": False,
            "has_h1_tag": False,
            "has_sitemap": False,
            "page_load_time_ms": None,
            "is_mobile_responsive": False,
            "recommendations": [],
            "status": "error",
            "error": None,
        }
    
    def analyze(self) -> Dict:
        """Run full analysis and return results."""
        try:
            # Check SSL
            self._check_ssl()
            
            # Fetch page
            response = self._fetch_page()
            if response is None:
                self.results["status"] = "error"
                return self.results
            
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Check SEO
            self._check_seo(soup)
            
            # Check mobile responsiveness
            self._check_mobile_responsive(soup)
            
            # Generate recommendations
            self._generate_recommendations()
            
            # Determine overall status
            self._determine_status()
            
        except Exception as e:
            self.results["error"] = str(e)
            self.results["status"] = "error"
        
        return self.results
    
    def _check_ssl(self) -> None:
        """Check if URL has valid SSL certificate."""
        try:
            parsed = urlparse(self.url)
            if parsed.scheme == "https":
                self.results["has_ssl"] = True
                # Verify SSL
                response = self.session.head(self.url, timeout=self.timeout, verify=True)
                self.results["ssl_valid"] = response.status_code < 400
            else:
                self.results["has_ssl"] = False
                self.results["ssl_valid"] = False
        except requests.exceptions.SSLError:
            self.results["has_ssl"] = True
            self.results["ssl_valid"] = False
        except Exception as e:
            self.results["error"] = f"SSL check failed: {str(e)}"
    
    def _fetch_page(self) -> requests.Response | None:
        """Fetch page and measure load time."""
        try:
            start = time.time()
            response = self.session.get(
                self.url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=False  # Allow self-signed certs for analysis
            )
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            self.results["page_load_time_ms"] = int(elapsed)
            
            if response.status_code >= 400:
                self.results["error"] = f"HTTP {response.status_code}"
                return None
            
            return response
        except requests.exceptions.Timeout:
            self.results["error"] = "Request timeout"
            return None
        except Exception as e:
            self.results["error"] = str(e)
            return None
    
    def _check_seo(self, soup: BeautifulSoup) -> None:
        """Check SEO metrics."""
        seo_score = 0
        
        # Check meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            self.results["has_meta_description"] = True
            seo_score += 20
        
        # Check H1 tags
        h1 = soup.find("h1")
        if h1:
            self.results["has_h1_tag"] = True
            seo_score += 20
        
        # Check title
        title = soup.find("title")
        if title and title.string:
            seo_score += 15
        
        # Check for headings hierarchy
        h2_count = len(soup.find_all("h2"))
        if h2_count > 0:
            seo_score += 10
        
        # Check for images with alt text
        images = soup.find_all("img")
        if images:
            alt_count = sum(1 for img in images if img.get("alt"))
            if alt_count / len(images) > 0.8:
                seo_score += 15
        
        # Check for sitemap
        try:
            sitemap_url = urljoin(self.url, "/sitemap.xml")
            resp = self.session.head(sitemap_url, timeout=5, verify=False)
            if resp.status_code < 400:
                self.results["has_sitemap"] = True
                seo_score += 20
        except:
            pass
        
        # Check for robots.txt
        try:
            robots_url = urljoin(self.url, "/robots.txt")
            resp = self.session.head(robots_url, timeout=5, verify=False)
            if resp.status_code < 400:
                seo_score += 10
        except:
            pass
        
        self.results["seo_score"] = min(seo_score, 100)
    
    def _check_mobile_responsive(self, soup: BeautifulSoup) -> None:
        """Check if site has mobile viewport meta tag."""
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if viewport and viewport.get("content"):
            self.results["is_mobile_responsive"] = True
    
    def _generate_recommendations(self) -> None:
        """Generate actionable recommendations."""
        recommendations = []
        
        # SSL recommendations
        if not self.results["has_ssl"]:
            recommendations.append({
                "priority": "critical",
                "title": "Add HTTPS/SSL Certificate",
                "description": "Your site is not using HTTPS. This is essential for security and SEO.",
                "action": "Install an SSL certificate (free via Let's Encrypt)"
            })
        elif not self.results["ssl_valid"]:
            recommendations.append({
                "priority": "high",
                "title": "Fix SSL Certificate Issues",
                "description": "Your SSL certificate has issues or is expired.",
                "action": "Renew or fix your SSL certificate"
            })
        
        # SEO recommendations
        if not self.results["has_meta_description"]:
            recommendations.append({
                "priority": "high",
                "title": "Add Meta Description",
                "description": "Meta descriptions help with SEO and click-through rates.",
                "action": "Add a compelling meta description (150-160 chars)"
            })
        
        if not self.results["has_h1_tag"]:
            recommendations.append({
                "priority": "high",
                "title": "Add H1 Heading",
                "description": "Pages should have exactly one H1 tag for proper structure.",
                "action": "Add a descriptive H1 heading to your page"
            })
        
        if not self.results["has_sitemap"]:
            recommendations.append({
                "priority": "medium",
                "title": "Create XML Sitemap",
                "description": "Sitemaps help search engines index your content.",
                "action": "Generate and submit an XML sitemap"
            })
        
        # Performance recommendations
        if self.results["page_load_time_ms"] and self.results["page_load_time_ms"] > 3000:
            recommendations.append({
                "priority": "high",
                "title": "Improve Page Load Speed",
                "description": f"Your page takes {self.results['page_load_time_ms']}ms to load. Target: <2000ms",
                "action": "Optimize images, enable caching, minify CSS/JS"
            })
        
        # Mobile recommendations
        if not self.results["is_mobile_responsive"]:
            recommendations.append({
                "priority": "critical",
                "title": "Make Site Mobile Responsive",
                "description": "Most users browse on mobile. Your site needs responsive design.",
                "action": "Implement responsive design or use a mobile-friendly framework"
            })
        
        self.results["recommendations"] = recommendations
    
    def _determine_status(self) -> None:
        """Determine overall health status."""
        critical_issues = sum(
            1 for r in self.results["recommendations"]
            if r.get("priority") == "critical"
        )
        high_issues = sum(
            1 for r in self.results["recommendations"]
            if r.get("priority") == "high"
        )
        
        if critical_issues > 0:
            self.results["status"] = "critical"
        elif high_issues > 2:
            self.results["status"] = "critical"
        elif high_issues > 0:
            self.results["status"] = "warning"
        else:
            self.results["status"] = "healthy"


def analyze_website(url: str) -> Dict:
    """Convenience function to analyze a website."""
    analyzer = WebsiteAnalyzer(url)
    return analyzer.analyze()


def batch_analyze_websites(urls: List[str]) -> List[Dict]:
    """Analyze multiple websites."""
    results = []
    for url in urls:
        try:
            result = analyze_website(url)
            results.append(result)
        except Exception as e:
            results.append({
                "url": url,
                "error": str(e),
                "status": "error"
            })
    return results
