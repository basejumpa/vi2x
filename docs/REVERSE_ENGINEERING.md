# Reverse Engineering and Legal Considerations

## Purpose

This project provides an independently developed converter from a proprietary binary 3D data format to the open Polygon File Format (PLY) and also GLB Format.

Its purpose is to enable interoperability with existing 3D data, allowing users to access, process, visualize, and exchange their data using standard tools and applications.

The converter is not affiliated with, endorsed by, or sponsored by the original format's developer or rights holder.

## Reverse Engineering Methodology

The converter was developed privately by examining lawfully obtained binary 3D data files. The analysis focused on identifying the file structure and the representation of 3D geometry and related attributes, followed by an independent implementation that converts those structures to PLY.

The development process, as reported by the author, involved:

1. **Binary file analysis:** Examining the structure and content of data files to identify their encoding conventions.
2. **Format interpretation:** Determining how the file format represents geometry and any associated attributes.
3. **Independent implementation:** Writing a converter to interpret the binary format and export PLY data.
4. **Validation:** Comparing the resulting converted data with expected geometry and properties, where suitable reference data is available.

The author reports that:

- The input files were lawfully obtained.
- The work was performed privately, independently of employment duties.
- No decompilation or disassembly of proprietary executable software was involved.
- No encryption or technical access protection was circumvented.

**Before publication:** Verify that the repository contains no copied proprietary source code, unauthorized sample data, confidential documentation, or other third-party materials that cannot lawfully be redistributed. Also verify that no confidentiality or contractual restrictions apply to the format information or to the files used during development.

## Legal Basis Under German and EU Law

The following provisions and judgment support independent interoperability implementations under specified circumstances. Their applicability depends on the facts and does not amount to a blanket authorization to reverse engineer or distribute any particular material.

### 1. Copyright Protection of File Formats

Section 69a(2) of the German Copyright Act (*Urheberrechtsgesetz*, UrhG) provides that ideas and principles underlying elements of a computer program, including interface-related principles, are not protected by copyright in computer programs.

In **Court of Justice of the European Union, Case C-406/10, *SAS Institute Inc. v World Programming Ltd* (2 May 2012)**, the Court held that the functionality of a computer program, its programming language, and the format of data files used to exploit certain functions do not, as such, constitute protected expression of the program under the EU software copyright rules.

Accordingly, independently implementing compatibility with a binary data format does not *by itself* infringe copyright in the software that uses that format. This does not exclude other potential rights or protection for original expressive material.

References:

- [§ 69a UrhG](https://www.gesetze-im-internet.de/urhg/__69a.html)
- [CJEU judgment, Case C-406/10](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62010CJ0406)

### 2. Observation and Testing of Software

Section 69d(3) UrhG permits a person entitled to use a copy of a computer program to observe, study, or test its functioning to determine underlying ideas and principles while carrying out authorized program-use activities.

This provision concerns analysis of *software*. The author reports analyzing binary data files rather than decompiling executable software, so this provision is included as background and is not the central basis for this project's development method.

Reference: [§ 69d UrhG](https://www.gesetze-im-internet.de/urhg/__69d.html)

### 3. Decompilation for Interoperability

Section 69e UrhG permits certain acts of software decompilation when indispensable to obtain information necessary for interoperability with an independently created program, subject to statutory conditions and restrictions on the use and disclosure of that information.

The author reports that no proprietary program was decompiled. This provision is included for context, not as a claim that the converter required or qualified for the decompilation exception.

Reference: [§ 69e UrhG](https://www.gesetze-im-internet.de/urhg/__69e.html)

### 4. Trade Secrets and Reverse Engineering

Section 3(1) of the German Trade Secrets Act (*Geschäftsgeheimnisgesetz*, GeschGehG) recognizes certain forms of acquisition of trade secrets by observing, studying, disassembling, or testing products or objects, including subject to conditions concerning lawful possession and obligations restricting acquisition.

The law does not provide an unconditional right to use or disclose information protected by confidentiality obligations. Whether the file format or related information constitutes a trade secret, and whether any contractual limitations apply, must be evaluated separately.

Reference: [§ 3 GeschGehG](https://www.gesetze-im-internet.de/geschgehg/__3.html)

## Ownership and Independence

The converter's original implementation is distinct from the original proprietary software or its documentation. An open-source license can be granted only by the party holding the necessary rights in the converter.

Under § 69b UrhG, economic exploitation rights in software created by an employee in the execution of employment duties or following employer instructions generally belong to the employer, unless otherwise agreed. Although the author reports private, independent development, relevant employment or contractual obligations should still be reviewed before publication.

Reference: [§ 69b UrhG](https://www.gesetze-im-internet.de/urhg/__69b.html)

## Repository and Distribution Principles

- Distribute only independently written source code and dependencies whose licenses permit redistribution.
- Do not include proprietary executable software or proprietary libraries without permission.
- Do not publish third-party binary test files unless their redistribution is authorized; prefer synthetic or appropriately licensed examples.
- Do not reproduce confidential specifications, documentation, or protected material.
- Do not suggest endorsement or affiliation with the original rights holder.
- Keep the actual open-source grant in a separate `LICENSE` file.

## Scope and Limitations

This project seeks data-format interoperability; it does not claim ownership of the original proprietary format, the software that produces it, or third-party trademarks.

The analysis above does not address every possible issue, including patent claims, particular license restrictions, confidentiality agreements, legal protection of technical measures, or rules outside Germany and the European Union.

## Disclaimer

This document explains the project's reported development method and the principal German and EU legal considerations relevant to independent file-format implementations. It is informational only and is not legal advice, a legal opinion, or a guarantee that any specific use or distribution is lawful.

## Legal References

1. [§ 69a UrhG — Subject Matter of Protection](https://www.gesetze-im-internet.de/urhg/__69a.html)
2. [§ 69b UrhG — Computer Programs Created by Employees](https://www.gesetze-im-internet.de/urhg/__69b.html)
3. [§ 69d UrhG — Exceptions to Acts Requiring Authorization](https://www.gesetze-im-internet.de/urhg/__69d.html)
4. [§ 69e UrhG — Decompilation](https://www.gesetze-im-internet.de/urhg/__69e.html)
5. [§ 3 GeschGehG — Permitted Acts](https://www.gesetze-im-internet.de/geschgehg/__3.html)
6. [CJEU, Case C-406/10, *SAS Institute Inc. v World Programming Ltd*, Judgment of 2 May 2012](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62010CJ0406)
