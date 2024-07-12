# ----------------------------------------------------------------------------
# Copyright (c) 2024, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import subprocess
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import qiime2
from q2_types.feature_data import DNAFASTAFormat

from q2_viromics.checkv_analysis import checkv_analysis, checkv_end_to_end


class TestCheckvAnalysis(unittest.TestCase):
    @patch("q2_viromics.checkv_analysis.run_command")
    def test_checkv_end_to_end_success(self, mock_run_command):
        # Mock the paths
        mock_tmp = "/fake/tmp"
        mock_sequences = MagicMock(spec=DNAFASTAFormat)
        mock_sequences.path = "/fake/sequences"
        mock_database = MagicMock()
        mock_database.path = "/fake/database"
        mock_database_listdir = ["internal_db"]

        with patch("os.listdir", return_value=mock_database_listdir):
            # Call the function
            checkv_end_to_end(
                mock_tmp,
                mock_sequences,
                mock_database,
                num_threads=10,
            )

        # Expected command
        expected_cmd = [
            "checkv",
            "end_to_end",
            "/fake/sequences",
            mock_tmp,
            "-d",
            "/fake/database/internal_db",
            "-t",
            "10",
        ]

        # Assert the command was called
        mock_run_command.assert_called_once_with(expected_cmd)

    @patch(
        "q2_viromics.checkv_analysis.run_command",
        side_effect=subprocess.CalledProcessError(1, "cmd"),
    )
    def test_checkv_end_to_end_failure(self, mock_run_command):
        # Mock the paths
        mock_tmp = "/fake/tmp"
        mock_sequences = MagicMock(spec=DNAFASTAFormat)
        mock_sequences.path = "/fake/sequences"
        mock_database = MagicMock()
        mock_database.path = "/fake/database"
        mock_database_listdir = ["internal_db"]

        with patch("os.listdir", return_value=mock_database_listdir):
            # Call the function and assert it raises an Exception
            with self.assertRaises(Exception) as context:
                checkv_end_to_end(
                    mock_tmp,
                    mock_sequences,
                    mock_database,
                    num_threads=10,
                )

            self.assertTrue(
                "An error was encountered while running checkv end_to_end"
                in str(context.exception)
            )

    @patch("q2_viromics.checkv_analysis.checkv_end_to_end")
    @patch("q2_viromics.checkv_analysis.DNAFASTAFormat")
    @patch("q2_viromics.checkv_analysis.pd.read_csv")
    @patch("shutil.copy")
    @patch("tempfile.TemporaryDirectory")
    def test_checkv_analysis_success(
        self,
        mock_tempdir,
        mock_shutil_copy,
        mock_read_csv,
        mock_DNAFASTAFormat,
        mock_checkv_end_to_end,
    ):
        # Mock the context managers
        mock_tempdir.return_value.__enter__.return_value = "/fake/tmp"

        # Mock the data frames with string indices
        mock_quality_summary_df = pd.DataFrame({"mock": ["data"]}, index=["sample_1"])
        mock_contamination_df = pd.DataFrame({"mock": ["data"]}, index=["sample_2"])
        mock_completeness_df = pd.DataFrame({"mock": ["data"]}, index=["sample_3"])
        mock_complete_genomes_df = pd.DataFrame({"mock": ["data"]}, index=["sample_4"])
        mock_read_csv.side_effect = [
            mock_quality_summary_df,
            mock_contamination_df,
            mock_completeness_df,
            mock_complete_genomes_df,
        ]

        # Mock the sequences and database
        mock_sequences = MagicMock(spec=DNAFASTAFormat)
        mock_sequences.path = "/fake/sequences"
        mock_database = MagicMock()
        mock_database.path = "/fake/database"

        # Call the function
        result = checkv_analysis(mock_sequences, mock_database, num_threads=10)

        # Assertions
        mock_checkv_end_to_end.assert_called_once_with(
            "/fake/tmp", mock_sequences, mock_database, 10
        )
        mock_shutil_copy.assert_any_call("/fake/tmp/viruses.fna", str(result[0]))
        mock_shutil_copy.assert_any_call("/fake/tmp/proviruses.fna", str(result[1]))
        mock_read_csv.assert_any_call(
            "/fake/tmp/quality_summary.tsv",
            sep="\t",
            na_values=["NA", "", "NaN"],
            index_col=0,
        )
        mock_read_csv.assert_any_call(
            "/fake/tmp/contamination.tsv",
            sep="\t",
            na_values=["NA", "", "NaN"],
            index_col=0,
        )
        mock_read_csv.assert_any_call(
            "/fake/tmp/completeness.tsv",
            sep="\t",
            na_values=["NA", "", "NaN"],
            index_col=0,
        )
        mock_read_csv.assert_any_call(
            "/fake/tmp/complete_genomes.tsv",
            sep="\t",
            na_values=["NA", "", "NaN"],
            index_col=0,
        )

        # Convert the DataFrame to Metadata
        expected_quality_summary_metadata = qiime2.Metadata(mock_quality_summary_df)
        expected_contamination_metadata = qiime2.Metadata(mock_contamination_df)
        expected_completeness_metadata = qiime2.Metadata(mock_completeness_df)
        expected_complete_genomes_metadata = qiime2.Metadata(mock_complete_genomes_df)

        # Verify the Metadata
        self.assertEqual(result[2], expected_quality_summary_metadata)
        self.assertEqual(result[3], expected_contamination_metadata)
        self.assertEqual(result[4], expected_completeness_metadata)
        self.assertEqual(result[5], expected_complete_genomes_metadata)


if __name__ == "__main__":
    unittest.main()